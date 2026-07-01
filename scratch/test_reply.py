import asyncio
import os
import sys
from dotenv import load_dotenv

# Add app to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()

from app.db.supabase_client import get_supabase
from app.db.tables.discovery import get_opportunity_by_id
from app.db.tables.projects import get_brand_profile_by_project, get_project_by_id
from app.services.product.copilot.reply import generate_reply

def main():
    db = next(get_supabase())
    # Let's get the LinkedIn opportunity that failed
    opps = db.table('opportunities').select('*').eq('platform', 'linkedin').limit(1).execute().data
    if not opps:
        print("No LinkedIn opp found")
        return
    
    opp = opps[0]
    print(f"Testing reply generation for opp {opp['id']} (platform: {opp['platform']})")
    
    project = get_project_by_id(db, opp['project_id'])
    brand = get_brand_profile_by_project(db, opp['project_id'])
    
    prompts = db.table('prompt_templates').select('*').eq('project_id', opp['project_id']).execute().data
    
    try:
        content, rationale, _ = generate_reply(
            opportunity=opp,
            brand=brand,
            prompts=prompts,
            platform=opp['platform']
        )
        print("SUCCESS!")
        print("Content:", content)
        print("Rationale:", rationale)
    except Exception as e:
        print("FAILED!")
        print(str(e))

if __name__ == "__main__":
    main()
