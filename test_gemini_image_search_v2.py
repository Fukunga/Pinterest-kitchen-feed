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
Search the live web using Google Search to find the direct main product image URL for the product '{product_name}' on Amazon.com (ASIN: {asin}).
Look for high-quality images hosted on 'media-amazon.com' or 'ssl-images-amazon.com'.
Return ONLY the direct link to the image file (ending in .jpg). No markdown, no introduction, just the raw URL.
"""

print("Asking Gemini to search for the image URL using search tool...")
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
