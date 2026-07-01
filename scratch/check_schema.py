from app.db.supabase_client import get_supabase_client
db = get_supabase_client()
res = db.table("company_profiles").select("*").limit(1).execute()
print("company_profiles columns:", res.data[0].keys() if res.data else "Empty table")
