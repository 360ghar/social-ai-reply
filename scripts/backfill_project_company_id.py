"""Backfill company_id on projects table based on company_profiles.workspace_id."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["ENVIRONMENT"] = "development"

for line in open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

from supabase import create_client
from app.core.config import Settings
settings = Settings()

supabase = create_client(settings.supabase_url, settings.supabase_secret_key)

# Get all companies
companies = supabase.table("company_profiles").select("id, workspace_id").execute()
company_by_ws = {c["workspace_id"]: c["id"] for c in companies.data if c.get("workspace_id")}

# Get all projects with NULL company_id
projects = supabase.table("projects").select("id, name, workspace_id, company_id").is_("company_id", "null").execute()
print(f"Projects with NULL company_id: {len(projects.data)}")

updated = 0
for p in projects.data:
    ws_id = p.get("workspace_id")
    company_id = company_by_ws.get(ws_id)
    if company_id:
        supabase.table("projects").update({"company_id": company_id}).eq("id", p["id"]).execute()
        print(f"  Updated project {p['id']} ({p['name']}) -> company_id={company_id}")
        updated += 1
    else:
        print(f"  Skipped project {p['id']} ({p['name']}) — no company found for workspace {ws_id}")

print(f"\nDone. {updated} projects updated.")
