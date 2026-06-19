import os
import base64
import requests
import urllib3
from urllib.parse import urljoin
from dotenv import load_dotenv

load_dotenv(override=True)
# Suppress HTTPS insecure connection warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class WordPressAPI:
    def __init__(self):
        self.wp_url = os.getenv("WP_URL")
        self.username = os.getenv("WP_USERNAME")
        self.app_password = os.getenv("WP_APPLICATION_PASSWORD")
        
        if not all([self.wp_url, self.username, self.app_password]):
            raise ValueError("WP_URL, WP_USERNAME, and WP_APPLICATION_PASSWORD must be set in environmental variables or .env file.")
        
        # Format URL to ensure it has a trailing slash and correct path
        if not self.wp_url.endswith('/'):
            self.wp_url += '/'
        self.api_base_url = urljoin(self.wp_url, "wp-json/wp/v2/")
        
        # Setup authentication header (Basic Auth using Application Password)
        credential = f"{self.username}:{self.app_password}"
        encoded_credential = base64.b64encode(credential.encode("utf-8")).decode("utf-8")
        self.headers = {
            "Authorization": f"Basic {encoded_credential}",
        }

    def create_post(self, title, content, categories=None, tags=None, status="draft", featured_media_id=None):
        """
        Creates a new post on WordPress via REST API.
        status: 'draft' or 'publish'
        """
        url = urljoin(self.api_base_url, "posts")
        
        payload = {
            "title": title,
            "content": content,
            "status": status,
        }
        
        if categories:
            payload["categories"] = categories  # Expects list of category IDs
        if tags:
            payload["tags"] = tags  # Expects list of tag IDs
        if featured_media_id:
            payload["featured_media"] = featured_media_id

        response = None
        try:
            response = requests.post(url, json=payload, headers=self.headers, verify=False, timeout=20)
            response.raise_for_status()
            post_data = response.json()
            print(f"Successfully created post! URL: {post_data.get('link')}")
            return post_data
        except requests.exceptions.RequestException as e:
            print(f"Error creating post: {e}")
            if response is not None:
                print(f"Response: {response.text}")
            return None

    def upload_media(self, file_path, title=None):
        """
        Uploads an image file to WordPress Media Library.
        Returns the media ID of the uploaded image.
        """
        url = urljoin(self.api_base_url, "media")
        
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return None
            
        file_name = os.path.basename(file_path)
        mime_type = "image/jpeg"
        if file_name.lower().endswith(".png"):
            mime_type = "image/png"
        elif file_name.lower().endswith(".gif"):
            mime_type = "image/gif"

        headers = self.headers.copy()
        headers.update({
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Content-Type": mime_type
        })

        response = None
        try:
            with open(file_path, "rb") as img_file:
                file_data = img_file.read()
                
            response = requests.post(url, data=file_data, headers=headers, verify=False, timeout=30)
            response.raise_for_status()
            media_data = response.json()
            media_id = media_data.get("id")
            print(f"Successfully uploaded media! ID: {media_id}, Link: {media_data.get('source_url')}")
            return media_id
        except requests.exceptions.RequestException as e:
            print(f"Error uploading media: {e}")
            if response is not None:
                print(f"Response: {response.text}")
            return None

if __name__ == "__main__":
    # Quick connectivity and authentication test
    try:
        print("Testing WordPress connection...")
        wp = WordPressAPI()
        response = requests.get(urljoin(wp.api_base_url, "posts?per_page=1"), headers=wp.headers, verify=False, timeout=15)
        response.raise_for_status()
        print("Connection and Authentication SUCCESSFUL!")
    except Exception as e:
        print(f"Test Failed: {e}")
        print("Please check your .env credentials.")
