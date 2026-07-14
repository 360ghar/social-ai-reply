from app.db.supabase_client import get_supabase_client
db = get_supabase_client()
res = db.table("custom_scrapers").select("*").execute()
for r in res.data:
    print(f"Platform: {r.get('platform')}, Host: {r.get('api_host')}")
