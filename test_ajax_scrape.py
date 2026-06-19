import subprocess
import re

asin = "B07XDN8T5K"
url = f"https://www.amazon.com/gp/product/ajax/ref=dp_aod_NEW_mbc?asin={asin}&m=&deviceType=desktop&packName=&experienceId=aodAjaxMain"
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

print(f"Requesting Amazon AOD Ajax page for ASIN: {asin}...")
try:
    result = subprocess.run(
        ["curl", "-s", "-L", "-H", f"User-Agent: {user_agent}", "-H", "Accept-Language: en-US,en;q=0.9", url],
        capture_output=True,
        timeout=10
    )
    html_content = result.stdout.decode("utf-8", errors="ignore")
    print(f"HTML Length: {len(html_content)}")
    
    if "To discuss automated access to Amazon data please contact" in html_content:
        print("FAILED: Blocked by Amazon CAPTCHA on Ajax.")
    else:
        # Search for any media-amazon images
        urls = re.findall(r'https://[a-zA-Z0-9\.\-]+images[a-zA-Z0-9\.\-]+\.com/images/I/[a-zA-Z0-9\+\-\%_\.]+\.jpg', html_content)
        if urls:
            # Clean resizing parameter
            large_urls = [u for u in urls if not any(x in u for x in ["_SS", "_SR", "_SX38_", "_SY38_"])]
            selected = large_urls[0] if large_urls else urls[0]
            cleaned_url = re.sub(r'\._[^/]+\.jpg$', '.jpg', selected)
            print(f"SUCCESS: {cleaned_url}")
        else:
            print("No images found in Ajax HTML.")
except Exception as e:
    print(f"Error: {e}")
