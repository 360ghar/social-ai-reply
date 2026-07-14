from app.db.supabase_client import get_supabase_client
db = get_supabase_client()
res = db.table("custom_scrapers").delete().in_("platform", ["reddit", "linkedin", "instagram"]).execute()
print("Deleted broken custom scrapers:", res.data)
