import asyncio
import os
import sys
from dotenv import load_dotenv

# Add app to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

from app.services.infrastructure.platforms.linkedin import LinkedInAdapter
from app.services.infrastructure.platforms.twitter import TwitterAdapter

async def main():
    print("Testing LinkedIn...")
    linkedin = LinkedInAdapter()
    if not linkedin._available:
        print("LinkedIn adapter not available (missing key)")
    else:
        try:
            raw_data = await linkedin._get("/api/v1/search/posts", params={"keyword": "Eneba", "page": "1"})
            posts = raw_data.get("data", [])
            for p in posts[:2]:
                print("\n--- LINKEDIN POST KEYS ---")
                print(list(p.keys()))
                for k, v in p.items():
                    if isinstance(v, str) and len(v) > 20:
                        print(f"{k}: {v[:100]}...")
                    elif isinstance(v, dict):
                        print(f"{k}: DICT with keys {list(v.keys())}")
        except Exception as e:
            print(f"LinkedIn error: {e}")

    print("\n\nTesting Twitter...")
    twitter = TwitterAdapter()
    if not twitter._available:
        print("Twitter adapter not available (missing key)")
    else:
        try:
            raw_data = await twitter._post("/search/search", body={"query": "Eneba -is:retweet lang:en", "section": "top", "limit": 2})
            if isinstance(raw_data, dict):
                posts = raw_data.get("results", [])
            else:
                posts = raw_data
            for p in posts[:2]:
                print("\n--- TWITTER POST KEYS ---")
                print(list(p.keys()))
                for k, v in p.items():
                    if isinstance(v, str) and len(v) > 20:
                        print(f"{k}: {v[:100]}...")
                    elif isinstance(v, dict):
                        print(f"{k}: DICT with keys {list(v.keys())}")
        except Exception as e:
            print(f"Twitter error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
