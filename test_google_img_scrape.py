import requests
import re
from bs4 import BeautifulSoup

asin = "B07XDN8T5K"
url = f"https://www.google.com/search?q={asin}+site:media-amazon.com/images/I/&tbm=isch"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print(f"Searching image for ASIN {asin} on Google Images...")
try:
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {r.status_code}")
    
    # Extract all media-amazon urls
    # Google Images HTML contains URLs in various structures
    urls = re.findall(r'https://[a-zA-Z0-9\.\-]*images[a-zA-Z0-9\.\-]*\.com/images/I/[a-zA-Z0-9\+\-\%_\.]+\.jpg', r.text)
    
    # Decode double slashes or unicode escapes if any
    clean_urls = []
    for u in urls:
        u_decoded = u.replace('\\u003d', '=').replace('\\u0026', '&')
        clean_urls.append(u_decoded)
        
    print(f"Found {len(clean_urls)} candidate URLs:")
    for u in clean_urls[:5]:
        print(f"  {u}")
except Exception as e:
    print(f"Error: {e}")
