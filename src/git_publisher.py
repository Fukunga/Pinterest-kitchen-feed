import os
import subprocess
from dotenv import load_dotenv

class GitPublisher:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(base_dir, ".env")
        load_dotenv(env_path, override=True)
        
        self.username = os.getenv("GITHUB_USERNAME")
        self.repo = os.getenv("GITHUB_REPO")
        self.pat = os.getenv("GITHUB_PAT")
        self.base_dir = base_dir

    def push_updates(self, commit_message="Update feed and images"):
        """Commits and pushes changes in the workspace to GitHub."""
        if not all([self.username, self.repo, self.pat]):
            print("[GIT] ERROR: GITHUB_USERNAME, GITHUB_REPO, and GITHUB_PAT must be set in .env.")
            print("[GIT] Skipping automated GitHub push. Please push changes manually.")
            return False
            
        print(f"[GIT] Starting GitHub publish to {self.username}/{self.repo}...")
        
        # Construct authenticated remote URL: https://<username>:<token>@github.com/<username>/<repo>.git
        remote_url = f"https://{self.username}:{self.pat}@github.com/{self.username}/{self.repo}.git"
        
        try:
            # 1. Initialize git if not already done (in case workspace is not a repo)
            if not os.path.exists(os.path.join(self.base_dir, ".git")):
                print("[GIT] Initializing local Git repository...")
                subprocess.run(["git", "init"], cwd=self.base_dir, check=True)
                
            # 2. Add remote URL if not present or different
            # Check current remote url
            result = subprocess.run(["git", "remote", "get-url", "origin"], cwd=self.base_dir, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"[GIT] Adding remote 'origin'...")
                subprocess.run(["git", "remote", "add", "origin", remote_url], cwd=self.base_dir, check=True)
            else:
                current_url = result.stdout.strip()
                if current_url != remote_url:
                    print(f"[GIT] Updating remote 'origin' URL...")
                    subprocess.run(["git", "remote", "set-url", "origin", remote_url], cwd=self.base_dir, check=True)
            
            # Ensure branch is main
            subprocess.run(["git", "branch", "-M", "main"], cwd=self.base_dir, check=True)
            
            # 3. Add all files
            print("[GIT] Staging changes (git add .)...")
            subprocess.run(["git", "add", "."], cwd=self.base_dir, check=True)
            
            # 4. Commit changes
            # Check if there are changes to commit
            status_result = subprocess.run(["git", "status", "--porcelain"], cwd=self.base_dir, capture_output=True, text=True)
            if not status_result.stdout.strip():
                print("[GIT] No changes to commit.")
                return True
                
            print(f"[GIT] Committing changes: '{commit_message}'...")
            # Configure basic git user config if not set
            subprocess.run(["git", "config", "user.name", "KitchenBot"], cwd=self.base_dir, check=True)
            subprocess.run(["git", "config", "user.email", "bot@kitchen.saisaido.com"], cwd=self.base_dir, check=True)
            
            subprocess.run(["git", "commit", "-m", commit_message], cwd=self.base_dir, check=True)
            
            # 5. Push to GitHub
            print("[GIT] Pushing changes to GitHub 'main' branch...")
            subprocess.run(["git", "push", "-u", "origin", "main", "--force"], cwd=self.base_dir, check=True)
            
            print("[GIT] SUCCESS! Changes successfully pushed to GitHub Pages.")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"[GIT] ERROR during Git execution: {e}")
            return False
        except Exception as e:
            print(f"[GIT] Unexpected error: {e}")
            return False

if __name__ == "__main__":
    # Self test
    publisher = GitPublisher()
    publisher.push_updates("Bot manual publish test")
