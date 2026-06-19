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

asin = "B09M8H44NZ"
product_name = "Mini Bag Sealer Handheld Heat Sealer"

# Prompt designed to make Gemini act as a remote scraper using its Search Tool
prompt = f"""
I need you to find the active product image URL for '{product_name}' (Amazon US ASIN: {asin}).
Use the Google Search tool to query and browse 'https://www.amazon.com/dp/{asin}'.
From the page source, extract the URL of the main product image. It should be hosted on 'media-amazon.com' (e.g. 'https://m.media-amazon.com/images/I/71xyz.jpg' or similar).
Do not return legacy/placeholder links like 'images-na.ssl-images-amazon.com/images/P/...'.
If you can't scrape the Amazon page directly, query Google Images for '{product_name} {asin} site:media-amazon.com' and find the correct image URL from the search results.
Return ONLY the raw URL string (ending in .jpg). Do not wrap in markdown or JSON. Just return the clean URL.
"""

print("Asking Gemini to scrape/find the image URL using Search tool...")
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
