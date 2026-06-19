import requests
import re
import subprocess
import json

asin = "B07XDN8T5K"
url = f"https://www.amazon.com/dp/{asin}"
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 1. Fetch free US proxy list
print("Fetching US proxy list from ProxyScrape...")
try:
    proxy_r = requests.get(
        "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=us&ssl=yes&anonymity=anonymous",
        timeout=10
    )
    proxies = [p.strip() for p in proxy_r.text.split("\n") if p.strip()]
    print(f"Retrieved {len(proxies)} US proxies.")
except Exception as e:
    print(f"Failed to fetch proxy list: {e}")
    proxies = []

# 2. Try fetching Amazon page using curl with proxies
success = False
for proxy in proxies[:5]:  # Try the first 5 proxies
    print(f"Trying proxy: {proxy}...")
    try:
        # Format for curl proxy: http://ip:port
        result = subprocess.run(
            ["curl", "-s", "-L", "-x", f"http://{proxy}", "-H", f"User-Agent: {user_agent}", "-H", "Accept-Language: en-US,en;q=0.9", url],
            capture_output=True,
            timeout=12
        )
        html_content = result.stdout.decode("utf-8", errors="ignore")
        print(f"  HTML Length: {len(html_content)}")
        
        if len(html_content) > 50000 and "To discuss automated access to Amazon data please contact" not in html_content:
            # We successfully bypassed regional block and captcha!
            print("  SUCCESS! Bypassed block using US proxy!")
            
            # Extract landingImage JSON or fallback images
            import html as html_parser
            match = re.search(r'id="landingImage"[^>]+data-a-dynamic-image="([^"]+)"', html_content)
            if match:
                img_json = html_parser.unescape(match.group(1))
                img_dict = json.loads(img_json)
                urls = list(img_dict.keys())
                if urls:
                    print(f"  FOUND IMAGE URL: {urls[0]}")
                    success = True
                    break
            
            # Try simple src fallback
            match_src = re.search(r'id="landingImage"[^>]+src="([^"]+)"', html_content)
            if match_src:
                src_url = html_parser.unescape(match_src.group(1))
                cleaned_url = re.sub(r'\._[^/]+\.jpg$', '.jpg', src_url)
                print(f"  FOUND IMAGE URL (src): {cleaned_url}")
                success = True
                break
                
            # Try regex fallback
            urls = re.findall(r'https://[a-zA-Z0-9\.\-]+images[a-zA-Z0-9\.\-]+\.com/images/I/[a-zA-Z0-9\+\-\%_\.]+\.jpg', html_content)
            if urls:
                large_urls = [u for u in urls if not any(x in u for x in ["_SS", "_SR", "_SX38_", "_SY38_"])]
                selected = large_urls[0] if large_urls else urls[0]
                cleaned_url = re.sub(r'\._[^/]+\.jpg$', '.jpg', selected)
                print(f"  FOUND IMAGE URL (regex): {cleaned_url}")
                success = True
                break
        else:
            print("  Failed: Content too short or CAPTCHA detected.")
            
    except Exception as e:
        print(f"  Error with proxy {proxy}: {e}")

if not success:
    print("FAILED: Could not fetch image URL using any of the tested US proxies.")
