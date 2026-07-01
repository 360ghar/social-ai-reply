from app.services.product.docs import generate_markdown_report

try:
    generate_markdown_report(
        company={"name": "Flipkart"},
        keywords=["Flipkart", "ecommerce"],
        personas=[],
        opportunities=[]
    )
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
