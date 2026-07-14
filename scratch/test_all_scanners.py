import asyncio
from app.services.infrastructure.platforms.router import PlatformRouter
from app.db.supabase_client import get_supabase_client

async def test_scanners():
    print("Testing scanners for keywords: ['360ghar', 'real estate']")
    keywords = ["360ghar", "real estate"]
    
    # All supported platforms in PlatformRouter
    platforms = [
        "twitter", "linkedin", "instagram", "facebook", 
        "hackernews", "github", "reddit", "indiehackers"
    ]
    
    router = PlatformRouter(platforms=platforms)
    
    print("\n--- Running Scanners ---")
    results = await router.search_all(
        keywords=keywords,
        limit_per_platform=5,
        time_filter="week"
    )
    
    print("\n--- Results ---")
    
    counts = {p: 0 for p in platforms}
    for post in results:
        # Some posts might not have platform attribute depending on how they are returned, but UnifiedPost has it
        counts[post.platform] += 1
        
    for platform in platforms:
        print(f"{platform}: {counts[platform]} opportunities")

asyncio.run(test_scanners())
