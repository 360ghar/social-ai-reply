import asyncio
from duckduckgo_search import DDGS
from datetime import datetime

def test_ddg(site, query):
    print(f"\n--- Testing DDG for {site} ---")
    try:
        results = DDGS().text(f'site:{site} "{query}"', max_results=5)
        for r in results:
            print(f"Title: {r['title']}\nURL: {r['href']}\nBody: {r['body']}\n")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_ddg("linkedin.com/posts", "real estate")
    test_ddg("instagram.com/p", "real estate")
    test_ddg("reddit.com/r", "real estate")
