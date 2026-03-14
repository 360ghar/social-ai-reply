from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.services.llm import MockLLMProvider
from app.services.persona_engine import PersonaEngine
from app.schemas.persona import BusinessInputRequest


def setup_db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return session_local()


def test_persona_engine_generates_real_estate_adjacencies():
    db = setup_db()
    payload = BusinessInputRequest(
        business_description="I have a real estate app like 360Ghar",
        max_personas=8,
        default_min_followers=1200,
    )
    engine = PersonaEngine(MockLLMProvider())
    response = engine.build_plan(payload, db=db)

    assert len(response.targets) >= 5
    keywords = {item.keyword for item in response.targets}
    assert "local realtors" in keywords
    assert "mortgage brokers" in keywords
    assert len(response.discovery_seed.keywords) == len(response.targets)
    assert response.discovery_seed.keywords[0].min_followers == 1200
