import asyncio
from app.db.supabase_client import get_supabase_client
from app.services.product.master_pipeline import run_full_pipeline_stream

async def main():
    db = get_supabase_client()
    res = db.table("projects").select("*").limit(1).execute()
    if not res.data:
        print("No projects found!")
        return
    project = res.data[0]
    print(f"Testing project {project['id']} - {project['name']}")
    
    print("\n--- Testing Auto Pipeline ---")
    try:
        workspace = {"id": project["workspace_id"]}
        async for chunk in run_full_pipeline_stream("flipkart.com", workspace, db):
            if isinstance(chunk, str):
                import json
                try:
                    data = json.loads(chunk.split("data: ")[1])
                    print("Pipeline Log:", data.get("msg", data))
                except:
                    pass
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
