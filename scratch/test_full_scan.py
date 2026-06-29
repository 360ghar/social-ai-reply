import asyncio
from app.db.supabase_client import get_supabase_client
from app.services.product.platform_scanner import run_platform_scan

db = get_supabase_client()
res = db.table("projects").select("*").eq("id", 170).execute()
if not res.data:
    print("No project found")
else:
    project = res.data[0]
    print(f"Scanning for project {project['name']} (ID {project['id']})")
    stats = run_platform_scan(
        db=db,
        project=project,
        platforms=["reddit", "linkedin", "instagram", "twitter", "hackernews", "github", "indiehackers"]
    )
    print("Scan stats:", stats)
