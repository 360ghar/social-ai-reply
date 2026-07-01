from app.db.supabase_client import get_supabase_client

db = get_supabase_client()
res = db.table("projects").select("*").ilike("name", "%360ghar%").execute()
if res.data:
    project = res.data[0]
    print(f"Found project: {project['name']} (ID: {project['id']})")
    kws = db.table("discovery_keywords").select("keyword").eq("project_id", project["id"]).execute()
    print("Keywords:", [k["keyword"] for k in kws.data])
else:
    print("No 360ghar project found in DB")
