import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

import dotenv
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, ".env")
env_values = dotenv.dotenv_values(env_path)
api_key = env_values.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

asin = "B07XDN8T5K"
product_name = "Electric Jar Opener for Weak Hands"

prompt = f"""
Using Google Search, find the actual, active high-resolution product image URL hosted on Amazon's CDN for the product '{product_name}' (Amazon US ASIN: {asin}).
The URL MUST start with 'https://m.media-amazon.com/images/I/' followed by the unique image ID (e.g. 'https://m.media-amazon.com/images/I/71xyz.jpg').
Do NOT return the legacy 'images-na.ssl-images-amazon.com/images/P/...' format as it is deprecated and returns a blank 1x1 image.
Search specifically for the exact product listing images currently indexed on the web.
Return ONLY the raw URL string (ending in .jpg). No markdown, no markdown formatting (like ```), no text wrapper. Just the raw URL.
"""

print("Asking Gemini to search for the active m.media-amazon.com URL...")
try:
    response = client.models.generate_content(
        model='gemini-3.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )
    print("SUCCESS!")
    print(f"Response text: '{response.text}'")
except Exception as e:
    print(f"FAILED: {e}")
