import asyncio
from app.services.infrastructure.platforms.router import PlatformRouter

async def test_scanners():
    print("Testing scanners for keywords: ['flipkart']")
    keywords = ["flipkart"]
    
    platforms = [
        "twitter", "linkedin", "instagram",
        "hackernews", "github", "reddit", "indiehackers"
    ]
    
    router = PlatformRouter(platforms=platforms)
    
    print("\n--- Running Scanners ---")
    results = await router.search_all(
        keywords=keywords,
        limit_per_platform=10,
        time_filter="week"
    )
    
    print("\n--- Results ---")
    
    counts = {p: 0 for p in platforms}
    for post in results:
        # DDG adapters set the exact string (e.g. reddit, hackernews) as post.platform
        counts[post.platform] += 1
        
    for platform in platforms:
        print(f"{platform}: {counts[platform]} opportunities")

asyncio.run(test_scanners())
