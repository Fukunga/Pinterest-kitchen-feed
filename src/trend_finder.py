import os
import pandas as pd
import json
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

class TrendFinder:
    def __init__(self):
        # Force read directly from .env file using absolute path
        import dotenv
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(base_dir, ".env")
        env_values = dotenv.dotenv_values(env_path)
        self.api_key = env_values.get("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        self.client = genai.Client(api_key=self.api_key)
        self.products_csv = os.path.join(base_dir, "data", "products.csv")

    def fetch_trending_products(self):
        """
        Uses Gemini 3.5 Flash with Google Search grounding to find highly popular,
        trending kitchen gadgets on Amazon US / TikTok / Pinterest and retrieves their ASINs.
        """
        print("[INFO] Querying Gemini with Google Search to discover active Amazon US trends...")
        
        prompt = """
Search the live web (Amazon US Best Sellers, TikTok viral kitchen trends, and Pinterest kitchen hack boards) to find 5 highly popular and trending kitchen gadgets right now.
For each product, you MUST find:
1. The exact 10-digit Amazon US ASIN (Amazon Standard Identification Number) - double check that this ASIN actually exists on Amazon.com for this product.
2. The product name in English.
3. 2-3 target SEO keywords separated by space (e.g., "vegetable chopper spiralizer").
4. Its approximate price range (e.g. "$15-$25").

Return the result as a strictly valid raw JSON list of objects, where each object has these exact keys: "asin", "product_name", "keyword", "price_range".
Do not include any conversational filler, markdown fences like ```json, or extra characters. Just a clean JSON array of 5 trending gadgets.
"""

        try:
            # Call Gemini with official Google Search tool enabled for real-time web grounding
            response = self.client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    response_mime_type="application/json"
                )
            )
            
            raw_text = response.text.strip()
            
            # Robust JSON cleaning
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\n", "", raw_text)
                raw_text = re.sub(r"\n```$", "", raw_text)
                raw_text = raw_text.strip()
                
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                match = re.search(r"(\[.*\])", raw_text, re.DOTALL)
                if match:
                    data = json.loads(match.group(1))
                else:
                    raise
                    
            if not isinstance(data, list):
                raise ValueError("Expected a list of trending products from Gemini.")
                
            return data
            
        except Exception as e:
            print(f"[ERROR] Failed to fetch trends using Gemini Search: {e}")
            return []

    def update_product_catalog(self):
        """
        Discovers new trends and appends them to data/products.csv if they don't already exist.
        """
        trending_items = self.fetch_trending_products()
        if not trending_items:
            print("[INFO] No new trends fetched. Skipping catalog update.")
            return
            
        print(f"[INFO] Discovered {len(trending_items)} potential trending products from the web.")
        
        # Load existing products
        if os.path.exists(self.products_csv):
            existing_df = pd.read_csv(self.products_csv)
            # Ensure ASIN is string for matching
            existing_df["asin"] = existing_df["asin"].astype(str)
            existing_asins = set(existing_df["asin"].tolist())
        else:
            existing_df = pd.DataFrame(columns=["asin", "product_name", "keyword", "price_range"])
            existing_asins = set()
            
        new_records = []
        for item in trending_items:
            asin = str(item.get("asin", "")).strip()
            product_name = item.get("product_name", "").strip()
            keyword = item.get("keyword", "").strip()
            price_range = item.get("price_range", "").strip()
            
            # Validations
            if not asin or len(asin) != 10:
                print(f"[SKIP] Invalid ASIN length: {asin} for '{product_name}'")
                continue
                
            if asin in existing_asins:
                print(f"[SKIP] ASIN {asin} already exists in products.csv")
                continue
                
            print(f"[ADD] New Trend Discovered! - {product_name} (ASIN: {asin})")
            new_records.append({
                "asin": asin,
                "product_name": product_name,
                "keyword": keyword,
                "price_range": price_range
            })
            existing_asins.add(asin)
            
        if new_records:
            new_df = pd.DataFrame(new_records)
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
            updated_df.to_csv(self.products_csv, index=False)
            print(f"[SUCCESS] Appended {len(new_records)} new trending products to {self.products_csv}!")
        else:
            print("[INFO] No new unique trends found to append.")

if __name__ == "__main__":
    # Self-test
    finder = TrendFinder()
    finder.update_product_catalog()
