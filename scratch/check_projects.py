from app.db.supabase_client import get_supabase_client
db = get_supabase_client()
res = db.table("projects").select("*").limit(1).execute()
print("projects columns:", res.data[0].keys() if res.data else "Empty table")
