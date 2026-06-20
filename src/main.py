import os
import sys
import re
import requests
import pandas as pd
import urllib3
from datetime import datetime
from xml.sax.saxutils import escape
from dotenv import load_dotenv

from git_publisher import GitPublisher

# Suppress HTTPS insecure connection warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# File paths in the workspace
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH, override=True)

PRODUCTS_CSV = os.path.join(BASE_DIR, "data", "products.csv")
HISTORY_CSV = os.path.join(BASE_DIR, "data", "posting_history.csv")
FEED_XML_PATH = os.path.join(BASE_DIR, "feed.xml")
IMAGE_DIR = os.path.join(BASE_DIR, "images")

# Force read content generator
sys.path.append(os.path.join(BASE_DIR, "src"))
from content_generator import ContentGenerator

def search_image_url_via_gemini(product_name, asin):
    """
    Uses Gemini 3.5 Flash with Google Search grounding to find the active
    high-quality product image URL from Amazon CDN.
    """
    from google import genai
    from google.genai import types
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
        
    client = genai.Client(api_key=api_key)
    prompt = f"""
Search the live web using Google Search to find the direct product listing image URL hosted on Amazon's CDN for:
Product Name: '{product_name}' (Amazon US ASIN: {asin}).

Look for high-quality product images hosted on Amazon's image servers. 
The URL must be a direct link (starting with https and end in .jpg, .jpeg, or .png).
Look for CDN URLs containing '/images/I/' (e.g. 'https://m.media-amazon.com/images/I/71xyz.jpg' or similar).
Do NOT return the deprecated format containing '/images/P/' (such as 'images-na.ssl-images-amazon.com/images/P/...').

Return ONLY the raw URL string. No markdown formatting (no ```), no HTML, no explanation, no text wrapper. Just the URL.
If you cannot find any matching URL on the live web, reply exactly with: None
"""
    try:
        print(f"Scouting product image for ASIN {asin} via Gemini Google Search grounding...")
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        if response.text:
            text = response.text.strip()
            # Flexibly extract CDN URLs containing product image identifier (/images/I/)
            match = re.search(r'(https://[^\s\'"]+images[^\s\'"]+/images/I/[^\s\'"]+\.(?:jpg|jpeg|png))', text)
            if match:
                url = match.group(1)
                url = url.replace('`', '').replace('"', '').replace("'", "")
                print(f"Successfully discovered image URL via Gemini Web Search: {url}")
                return url
            else:
                # Broader fallback search for any amazon image CDN if /images/I/ is missing but still valid
                match_broad = re.search(r'(https://[^\s\'"]*(?:media-amazon\.com|images-amazon\.com)[^\s\'"]+\.(?:jpg|jpeg|png))', text)
                if match_broad:
                    url = match_broad.group(1)
                    url = url.replace('`', '').replace('"', '').replace("'", "")
                    if "/images/P/" not in url:
                        print(f"Successfully discovered image URL via Gemini Web Search (broad): {url}")
                        return url
    except Exception as e:
        print(f"Gemini image search failed: {e}")
    return None

def fetch_amazon_image_url(asin, product_name):
    """
    Scrapes the Amazon product page using curl to bypass Python requests TLS fingerprinting,
    extracting the high-resolution media-amazon product image URL dynamically.
    If blocked or failed, falls back to Google Search grounding via Gemini.
    """
    import subprocess
    import html as html_parser
    import json

    url = f"https://www.amazon.com/dp/{asin}"
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    print(f"Scouting product image for ASIN {asin} via system curl...")
    try:
        result = subprocess.run(
            ["curl", "-s", "-L", "-H", f"User-Agent: {user_agent}", "-H", "Accept-Language: en-US,en;q=0.9", url],
            capture_output=True,
            timeout=10
        )
        html_content = result.stdout.decode("utf-8", errors="ignore")
        
        # Method 1: Extract landingImage dynamic data JSON
        match = re.search(r'id="landingImage"[^>]+data-a-dynamic-image="([^"]+)"', html_content)
        if match:
            img_json = html_parser.unescape(match.group(1))
            try:
                img_dict = json.loads(img_json)
                urls = list(img_dict.keys())
                if urls:
                    print(f"Successfully scraped image URL via landingImage JSON: {urls[0]}")
                    return urls[0]
            except Exception:
                pass
                
        # Method 2: Check landingImage src attribute directly
        match_src = re.search(r'id="landingImage"[^>]+src="([^"]+)"', html_content)
        if match_src:
            src_url = html_parser.unescape(match_src.group(1))
            cleaned_url = re.sub(r'\._[^/]+\.jpg$', '.jpg', src_url)
            print(f"Successfully scraped image URL via landingImage src: {cleaned_url}")
            return cleaned_url

        # Method 3: Fallback to regex search for any Amazon image CDN paths
        urls = re.findall(r'https://[a-zA-Z0-9\.\-]+images[a-zA-Z0-9\.\-]+\.com/images/I/[a-zA-Z0-9\+\-\%_\.]+\.jpg', html_content)
        if urls:
            large_urls = [u for u in urls if not any(x in u for x in ["_SS", "_SR", "_SX38_", "_SY38_", "_SX50_", "_SY50_"])]
            selected = large_urls[0] if large_urls else urls[0]
            cleaned_url = re.sub(r'\._[^/]+\.jpg$', '.jpg', selected)
            print(f"Successfully scraped image URL via regex fallback: {cleaned_url}")
            return cleaned_url
            
    except Exception as e:
        print(f"Error fetching image for ASIN {asin} via curl: {e}")
        
    # Fallback to Gemini search
    print(f"Curl scraping failed for ASIN {asin}. Trying Gemini Web Search...")
    gemini_scraped = search_image_url_via_gemini(product_name, asin)
    if gemini_scraped:
        return gemini_scraped
        
    # Ultimate fallback: generate high-quality Flickr image URL based on product keywords
    clean_name = product_name.lower()
    
    # Split by with/for to cut off accessory/purpose phrases
    split_pattern = r'\b(with|for)\b'
    parts = re.split(split_pattern, clean_name, maxsplit=1)
    core_name = parts[0].strip()
    
    # Remove special characters, numbers and extra spaces
    core_name = re.sub(r'[^a-zA-Z\s]', ' ', core_name)
    
    # Filter out stopwords and generic terms
    stopwords = {
        "mini", "handheld", "electric", "portable", "gadget", "tool", 
        "kitchen", "best", "new", "top", "the", "a", "an", "of", "in", 
        "on", "at", "by", "to", "and", "or", "cover", "holder", "pack",
        "set", "pcs", "piece"
    }
    words = [w for w in core_name.split() if w not in stopwords]
    
    # Extract up to 2 keywords from the end of the filtered word list
    keywords = words[-2:] if len(words) >= 2 else (words if words else ["gadget"])
    keyword_str = ",".join(keywords)
    
    fallback_url = f"https://loremflickr.com/600/400/kitchen,{keyword_str}/all"
    
    print(f"WARNING: Amazon image retrieval failed. Using premium Flickr fallback image for queries '{keyword_str}': {fallback_url}")
    return fallback_url

def get_posted_asins():
    """Reads the posting history to avoid duplicate posts."""
    if os.path.exists(HISTORY_CSV):
        try:
            df = pd.read_csv(HISTORY_CSV)
            return set(df["asin"].astype(str).tolist())
        except Exception:
            return set()
    return set()

def record_post(asin, product_name, affiliate_url):
    """Records a successful post in the history file."""
    new_record = {
        "asin": asin,
        "product_name": product_name,
        "posted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "wp_post_id": 0,  # Legacy field, set to 0 for serverless
        "wp_post_url": affiliate_url  # Directly link to affiliate URL
    }
    
    if os.path.exists(HISTORY_CSV):
        df = pd.read_csv(HISTORY_CSV)
        df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
    else:
        df = pd.DataFrame([new_record])
        
    df.to_csv(HISTORY_CSV, index=False)
    print(f"Logged post history for ASIN: {asin}")

def generate_redirect_html(asin, affiliate_url):
    """Generates a static redirect HTML page for the product ASIN to bypass Pinterest domain claim limits."""
    redirect_dir = os.path.join(BASE_DIR, "dp", asin)
    os.makedirs(redirect_dir, exist_ok=True)
    html_path = os.path.join(redirect_dir, "index.html")
    
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Redirecting...</title>
    <link rel="canonical" href="{affiliate_url}">
    <meta http-equiv="refresh" content="0;url={affiliate_url}">
    <script>
        window.location.replace("{affiliate_url}");
    </script>
</head>
<body>
    <p>Redirecting to <a href="{affiliate_url}">Amazon</a>...</p>
</body>
</html>"""
    
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated redirect HTML for ASIN {asin} at {html_path}")
    return f"https://kitchen.saisaido.com/dp/{asin}/"

def clean_html_to_plain_text(html_content):
    """Simple parser to remove HTML tags and clean up whitespace for RSS description."""
    # Replace list items and paragraph breaks with spaces
    text = re.sub(r'</?(?:p|li|h1|h2|h3|tr|td|div)[^>]*>', ' ', html_content)
    # Remove all other HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove HTML entities
    text = html_content_parser = re.sub(r'&[a-zA-Z0-9#]+;', ' ', text)
    # Collapse multiple spaces/newlines
    text = re.sub(r'\s+', ' ', text).strip()
    # Replace curly quotes and apostrophes to standard ASCII to prevent XML/parser bugs
    text = text.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')
    return text

def update_feed_xml(title, affiliate_url, pub_date, asin, image_url, description_text):
    """Appends the new item to the feed.xml file safely by string replacement."""
    if not os.path.exists(FEED_XML_PATH):
        print(f"ERROR: feed.xml not found at {FEED_XML_PATH}. Cannot update feed.")
        return False
        
    try:
        with open(FEED_XML_PATH, "r", encoding="utf-8") as f:
            feed_content = f.read()
            
        escaped_title = escape(title)
        escaped_link = escape(affiliate_url)
        escaped_img = escape(image_url)
        
        # Add compliance hashtags (#ad #affiliate) to the description
        full_description = f"Check out this amazing {title} on Amazon! {description_text}"
        if len(full_description) > 450:
            full_description = full_description[:450] + "..."
        full_description += " #ad #affiliate"
        escaped_desc = escape(full_description)
        
        # Construct item XML
        new_item_xml = f"""		<item>
			<title>{escaped_title}</title>
			<link>{escaped_link}</link>
			<pubDate>{pub_date}</pubDate>
			<guid isPermaLink="false">{asin}</guid>
			<description>{escaped_desc}</description>
			<media:content url="{escaped_img}" type="image/jpeg" medium="image" />
		</item>"""
		
        # 1. Insert item right before the first <item> tag to maintain valid RSS metadata order
        item_pattern = r'(<item>)'
        match = re.search(item_pattern, feed_content)
        if not match:
            # Fallback to inserting under <channel> if no items exist yet
            channel_pattern = r'(<channel>[^<]*)'
            feed_content = re.sub(channel_pattern, f"\\1\n{new_item_xml}", feed_content, count=1)
        else:
            feed_content = re.sub(item_pattern, f"{new_item_xml}\n\\1", feed_content, count=1)
        
        # 2. Update <lastBuildDate>
        now_rfc = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
        feed_content = re.sub(r'<lastBuildDate>[^<]*</lastBuildDate>', f"<lastBuildDate>{now_rfc}</lastBuildDate>", feed_content)
        
        with open(FEED_XML_PATH, "w", encoding="utf-8") as f:
            f.write(feed_content)
            
        print(f"Successfully updated feed.xml with new item ASIN {asin}")
        return True
    except Exception as e:
        print(f"Failed to update feed.xml: {e}")
        return False

def main():
    # Force output encoding to utf-8 to prevent cp932 encoding errors on Windows
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    print("=== STARTING SERVERLESS KITCHEN GADGETS BOT ===")
    
    # 0. Automatically discover and update trending products from Amazon US / TikTok
    try:
        print("Scouting for latest Amazon US / TikTok kitchen trends...")
        from trend_finder import TrendFinder
        finder = TrendFinder()
        finder.update_product_catalog()
    except Exception as e:
        print(f"Trend Discovery failed (skipping): {e}")
        
    # 1. Load Configurations
    associate_tag = os.getenv("AMAZON_ASSOCIATE_TAG", "saisaido-20")
        
    # 2. Initialize Gemini API
    try:
        generator = ContentGenerator()
    except Exception as e:
        print(f"Initialization Failed: {e}")
        print("Please configure your .env file with valid keys and credentials first.")
        return

    # 3. Load Products and History
    if not os.path.exists(PRODUCTS_CSV):
        print(f"Error: Products file not found at {PRODUCTS_CSV}. Please run the seed setup first.")
        return
        
    products_df = pd.read_csv(PRODUCTS_CSV)
    posted_asins = get_posted_asins()
    
    # Get the keywords of already posted products to avoid posting similar products sequentially
    posted_products = products_df[products_df["asin"].astype(str).isin(posted_asins)]
    posted_keywords = set(posted_products["keyword"].dropna().tolist())
    
    # Try to find products that haven't been posted AND whose keyword (product type) hasn't been posted
    unposted_products = products_df[
        (~products_df["asin"].astype(str).isin(posted_asins)) & 
        (~products_df["keyword"].isin(posted_keywords))
    ]
    
    # If all product types (keywords) have been posted at least once, fall back to checking just unposted ASINs
    if unposted_products.empty:
        print("All unique product types (keywords) have been posted once! Posting remaining unique ASINs...")
        unposted_products = products_df[~products_df["asin"].astype(str).isin(posted_asins)]
    
    if unposted_products.empty:
        print("All products in the catalog have already been posted! Add more ASINs to data/products.csv.")
        return
        
    print(f"Found {len(unposted_products)} pending products. Processing the first one...")
    
    # Pick the first unposted product
    target_product = unposted_products.iloc[0]
    asin = str(target_product["asin"])
    product_name = target_product["product_name"]
    keyword = target_product["keyword"]
    
    # Generate Amazon affiliate link (US format)
    affiliate_url = f"https://www.amazon.com/dp/{asin}?tag={associate_tag}"
    print(f"Targeting: {product_name} (ASIN: {asin})")
    print(f"Generated Affiliate Link: {affiliate_url}")
    
    # 4. Generate Content via Gemini
    print("Generating engaging review article using Gemini API...")
    article = generator.generate_review(
        product_name=product_name,
        keyword=keyword,
        affiliate_url=affiliate_url
    )
    
    title = article["title"]
    raw_html_content = article["content"]
    plain_desc_text = clean_html_to_plain_text(raw_html_content)
    
    # 5. Fetch and download high-resolution image locally to images/ directory
    scraped_image = fetch_amazon_image_url(asin, product_name)
    if not scraped_image:
        scraped_image = "https://placehold.co/600x400/fafafa/e47911?text=Smart+Kitchen+Finds"
        
    image_filename = f"temp_{asin}.jpg"
    local_image_path = os.path.join(IMAGE_DIR, image_filename)
    
    print(f"Downloading image from {scraped_image} to host on GitHub Pages...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        img_resp = requests.get(scraped_image, headers=headers, timeout=20)
        img_resp.raise_for_status()
        os.makedirs(os.path.dirname(local_image_path), exist_ok=True)
        with open(local_image_path, "wb") as f:
            f.write(img_resp.content)
        print(f"Successfully saved image locally: {local_image_path}")
    except Exception as e:
        print(f"Failed to download image: {e}. Reverting to standard placeholder.")
        # Re-save a fallback image just in case
        fallback_url = "https://placehold.co/600x400/fafafa/e47911?text=Smart+Kitchen+Finds"
        try:
            img_resp = requests.get(fallback_url, timeout=15)
            with open(local_image_path, "wb") as f:
                f.write(img_resp.content)
        except Exception:
            pass
            
    # GitHub Pages URL structure for the image
    github_image_url = f"https://kitchen.saisaido.com/images/{image_filename}"
    
    # 6. Generate redirect HTML locally
    redirect_url = generate_redirect_html(asin, affiliate_url)
    
    # 7. Update feed.xml locally
    pub_date_rfc = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    print("Updating feed.xml...")
    feed_updated = update_feed_xml(
        title=title,
        affiliate_url=redirect_url,
        pub_date=pub_date_rfc,
        asin=asin,
        image_url=github_image_url,
        description_text=plain_desc_text
    )
    
    if feed_updated:
        # 8. Record to Posting History
        record_post(asin, product_name, redirect_url)
        
        # 8. Automated Git Commit & Push to GitHub Pages
        print("Publishing updates to GitHub Pages...")
        publisher = GitPublisher()
        published = publisher.push_updates(commit_message=f"Automated post: {product_name} (ASIN: {asin})")
        
        if published:
            print("=== BOT JOB COMPLETED SUCCESSFULLY ===")
        else:
            print("WARNING: Bot completed but failed to push updates to GitHub.")
            print("=== BOT JOB COMPLETED WITH WARNINGS ===")
    else:
        print("ERROR: Failed to update RSS feed.xml.")
        print("=== BOT JOB FAILED ===")

if __name__ == "__main__":
    main()
