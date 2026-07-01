from app.db.supabase_client import get_supabase_client
db = get_supabase_client()
res = db.table("company_profiles").select("id, name, website_url, created_at").execute()
for r in res.data:
    print(r)
