import requests

asin = "B07FVQLBL3"
urls_to_test = [
    f"https://images-fe.ssl-images-amazon.com/images/P/{asin}.01.LZZZZZZZ.jpg",
    f"https://images-na.ssl-images-amazon.com/images/P/{asin}.01.LZZZZZZZ.jpg",
    f"http://images.amazon.com/images/P/{asin}.01.LZZZZZZZ.jpg",
    f"https://ws-fe.amazon-adsystem.com/widgets/q?_encoding=UTF8&ASIN={asin}&Format=_SL400_&ID=AsinImage&MarketPlace=US&ServiceVersion=20070822&WS=1&tag=test-20",
]

for url in urls_to_test:
    try:
        r = requests.head(url, timeout=5, allow_redirects=True)
        print(f"URL: {url}")
        print(f"  Status: {r.status_code}")
        print(f"  Content-Length: {r.headers.get('Content-Length')}")
        print(f"  Content-Type: {r.headers.get('Content-Type')}")
    except Exception as e:
        print(f"URL: {url} -> Failed: {e}")
