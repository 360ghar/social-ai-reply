import asyncio
from app.db.supabase_client import get_supabase_client
from app.services.product.platform_scanner import run_platform_scan
import json

db = get_supabase_client()
# Get the most recent project
res = db.table("projects").select("*").order("created_at", desc=True).limit(1).execute()
project = res.data[0]

try:
    print(f"Running platform scan for project {project['id']}...")
    scan_res = run_platform_scan(
        db, project,
        platforms=["hackernews", "github", "reddit", "twitter"],
        limit_per_platform=2,
        time_filter="week"
    )
    print("SUCCESS! Output:")
    print(json.dumps(scan_res, indent=2))
except Exception as e:
    import traceback
    traceback.print_exc()
