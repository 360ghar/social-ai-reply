import asyncio
from app.services.product.relevance_v2 import RelevanceEngine
from app.services.product.scanner import CandidatePost
from datetime import datetime, timezone

def test():
    engine = RelevanceEngine()
    engine_brand = {
        "name": "Flipkart",
        "brand_name": "Flipkart",
        "description": "An ecommerce company",
        "product_summary": "An ecommerce company",
        "target_audience": "",
        "category": "",
        "pain_points": [],
        "competitors": ["Amazon"],
    }
    
    candidate = CandidatePost(
        title="Just a test post",
        body="body",
        platform="hackernews",
        source_name="hackernews",
        upvotes=10,
        comments_count=0,
        created_at=datetime.now(timezone.utc),
        author="test",
        post_url="http://test.com",
    )
    
    engine_kws = [{"keyword": "flipkart", "type": "core", "weight": 1.0}]
    
    res = engine.score(candidate, engine_brand, engine_kws)
    print("Scored!", res)

if __name__ == "__main__":
    test()
