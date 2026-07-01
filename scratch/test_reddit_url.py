import asyncio
import httpx
import urllib.parse
import random

async def test():
    query = "comparison shoppers OR flipkart"
    query_encoded = urllib.parse.quote_plus(query)
    url = f"https://www.reddit.com/search.json?q={query_encoded}&limit=2&sort=new"
    
    headers = {
        'User-Agent': f'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        res = await client.get(url, headers=headers)
        print("Reddit status:", res.status_code)
        
    url2 = f"https://api.github.com/search/issues?q={query_encoded}&per_page=2&sort=created"
    headers2 = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'
    }
    async with httpx.AsyncClient() as client:
        res = await client.get(url2, headers=headers2)
        print("GitHub status:", res.status_code)

asyncio.run(test())
