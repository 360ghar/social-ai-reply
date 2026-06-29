from app.db.supabase_client import get_supabase_client
db = get_supabase_client()
for table in ["opportunities", "personas", "keywords", "brand_keywords", "projects"]:
    try:
        res = db.table(table).select("*").limit(1).execute()
        if res.data:
            print(f"{table} columns: {list(res.data[0].keys())}")
        else:
            print(f"{table} is empty, can't infer schema easily this way")
    except Exception as e:
        print(f"Error reading {table}: {e}")
