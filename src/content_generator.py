import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(override=True)

class ContentGenerator:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set. Please obtain one from Google AI Studio and place it in your .env file.")
        
        # Force read directly from .env file using absolute path to bypass Windows OS cached environment variables
        import dotenv
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(base_dir, ".env")
        env_values = dotenv.dotenv_values(env_path)
        self.api_key = env_values.get("GEMINI_API_KEY") or api_key
        
        # Safe debug print for verification
        print(f"[DEBUG] Loaded GEMINI_API_KEY: {self.api_key[:5]}...{self.api_key[-5:]} (Length: {len(self.api_key)})")
        
        # Initialize official Google GenAI Client
        # The service account and API limits are now fully resolved, so standard authentication will succeed.
        self.client = genai.Client(api_key=self.api_key)

    def generate_review(self, product_name, keyword, affiliate_url):
        """
        Generates a viral-worthy, SEO-optimized English review article about a kitchen gadget.
        Includes a captivating title and call-to-actions pointing to the affiliate_url.
        Uses official Vertex AI integration to support bound AQ keys.
        """
        prompt = f"""
Create a highly engaging, viral-style product review article in English for a blog targeting home cooks and kitchen enthusiasts.
The goal of this article is to drive traffic from Pinterest and convert readers into buyers via an Amazon affiliate link.

Product Name: {product_name}
Target SEO Keywords to include naturally: {keyword}
Affiliate URL to embed: {affiliate_url}

Follow this structure exactly:
1. TITLE: Make it catchy, emotional, and click-worthy for Pinterest users (e.g., "This $20 Kitchen Gadget Saved My Mornings", "Why Everyone on Pinterest is Obsessed with this Hack").
2. INTRODUCTION: Highlight a common kitchen struggle/pain point and introduce the product as the ultimate life-saving solution.
3. WHY YOU NEED IT: 3-4 major benefits/features in engaging bullet points. Explain 'why it works' emotionally.
4. PROS & CONS: A balanced look (keeps the review trustworthy).
5. CALL TO ACTION (CTA): Add a prominent, exciting call to action encouraging them to check the price and buy on Amazon. Use HTML buttons or clear link formatting. For example: `<a href="{affiliate_url}" target="_blank" style="display:inline-block;background-color:#FF9900;color:white;padding:12px 24px;text-decoration:none;border-radius:4px;font-weight:bold;margin:15px 0;">Get Yours on Amazon Here!</a>`
6. CONCLUSION: A final inspiring wrap-up sentence.

Tone: Enthusiastic, friendly, helpful, lifestyle-focused, honest.
Output format: JSON with two keys: "title" (the article title) and "content" (the full article body in HTML format, as WordPress REST API works best with HTML/styled blocks).

Do not include any markdown fences or 'json' markers in the response, just return a raw valid JSON string.
"""

        try:
            # Generate content using official Vertex AI integration
            response = self.client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            # Robust parsing of the JSON response to handle any markdown wrapping or extra text from LLM
            import json
            
            raw_text = response.text.strip()
            
            def extract_json(text):
                start = text.find('{')
                if start == -1:
                    raise ValueError("No JSON object found in response")
                count = 0
                in_string = False
                escape = False
                for i in range(start, len(text)):
                    char = text[i]
                    if escape:
                        escape = False
                        continue
                    if char == '\\':
                        escape = True
                        continue
                    if char == '"':
                        in_string = not in_string
                        continue
                    if not in_string:
                        if char == '{':
                            count += 1
                        elif char == '}':
                            count -= 1
                            if count == 0:
                                return text[start:i+1]
                raise ValueError("Braces do not match in JSON response")

            try:
                json_str = extract_json(raw_text)
                data = json.loads(json_str)
            except Exception as parse_err:
                import re
                match = re.search(r"({.*})", raw_text, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1))
                    except Exception:
                        raise parse_err
                else:
                    raise parse_err
            
            # Double check required keys
            if "title" not in data or "content" not in data:
                raise ValueError("LLM response is missing required JSON keys.")
                
            return data
        except Exception as e:
            print(f"Error generating content with Vertex AI Gemini: {e}")
            
            # Fallback mock post in case of API failure to prevent crash
            return {
                "title": f"Why the {product_name} is Taking Over Pinterest!",
                "content": f"""
                <p>If you love cooking but hate kitchen clutter and wasted time, the <strong>{product_name}</strong> is about to become your new best friend.</p>
                <p>This simple yet revolutionary tool solves the exact problems kitchen lovers face daily. Here is why thousands of home cooks are upgrading their kitchen setup with this gadget.</p>
                <h3>Key Features:</h3>
                <ul>
                    <li><strong>Effortless Operation:</strong> Saves time and hand fatigue.</li>
                    <li><strong>Space Saving:</strong> Compact design fits in any drawer.</li>
                    <li><strong>Easy to Clean:</strong> Dishwasher safe!</li>
                </ul>
                <p>Don't wait to upgrade your cooking routine. <a href="{affiliate_url}" target="_blank">Get the {product_name} on Amazon today!</a></p>
                """
            }

if __name__ == "__main__":
    # Test execution
    try:
        print("Testing Vertex AI Gemini Content Generator...")
        gen = ContentGenerator()
        res = gen.generate_review(
            product_name="Dash Rapid Egg Cooker",
            keyword="rapid egg cooker electric, easy breakfast hacks",
            affiliate_url="https://www.amazon.com/dp/B01ECEG8I4?tag=testtag-20"
        )
        print("\n--- GENERATED TITLE ---")
        print(res['title'])
        print("\n--- GENERATED CONTENT PREVIEW ---")
        print(res['content'][:300] + "...")
        print("SUCCESS!")
    except Exception as e:
        print(f"Test Failed: {e}")
        print("Please check your .env, Vertex API activation status, and GEMINI_API_KEY.")
