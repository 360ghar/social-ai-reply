import asyncio
from app.db.supabase_client import get_supabase_client
from app.services.product.platform_scanner import _async_platform_scan
import json

db = get_supabase_client()
res = db.table("projects").select("*").limit(1).execute()
project = res.data[0]

async def main():
    print("Running _async_platform_scan direct...")
    try:
        scan_res = await _async_platform_scan(
            platforms=["hackernews", "github", "reddit"],
            search_keywords=["flipkart"],
            limit_per_platform=2,
            subreddits=["appleindia"],
            workspace_id=project["workspace_id"],
            db=db
        )
        print("SUCCESS! Output length:", len(scan_res))
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
