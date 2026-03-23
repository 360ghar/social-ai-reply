from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import TargetKeyword
from app.schemas.persona import (
    AdjacentPersona,
    BusinessInputRequest,
    DiscoverySeed,
    KeywordSeed,
    PersonaPlanResponse,
)
from app.services.llm import LLMProvider, MockLLMProvider


class PersonaEngine:
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    def build_plan(self, payload: BusinessInputRequest, db: Session | None = None) -> PersonaPlanResponse:
        raw_targets = self.llm_provider.generate_adjacent_personas(
            business_description=payload.business_description,
            locale=payload.locale,
            max_personas=payload.max_personas,
        )
        if not raw_targets:
            raw_targets = MockLLMProvider().generate_adjacent_personas(
                business_description=payload.business_description,
                locale=payload.locale,
                max_personas=payload.max_personas,
            )

        targets: list[AdjacentPersona] = []
        for item in raw_targets:
            try:
                targets.append(AdjacentPersona.model_validate(item))
            except Exception:
                continue

        generated_at = datetime.now(timezone.utc)
        if db is not None:
            self._persist_targets(db, payload.business_description, targets)

        discovery_seed = DiscoverySeed(
            business_description=payload.business_description,
            generated_at=generated_at,
            keywords=[
                KeywordSeed(
                    keyword=t.keyword,
                    profile_type=t.profile_type,
                    priority_score=t.priority_score,
                    min_followers=payload.default_min_followers,
                )
                for t in targets
            ],
        )
        return PersonaPlanResponse(
            business_description=payload.business_description,
            generated_at=generated_at,
            targets=targets,
            discovery_seed=discovery_seed,
        )

    def _persist_targets(self, db: Session, business_input: str, targets: list[AdjacentPersona]) -> None:
        for target in targets:
            existing = db.scalar(
                select(TargetKeyword).where(
                    TargetKeyword.business_input == business_input,
                    TargetKeyword.keyword == target.keyword,
                    TargetKeyword.profile_type == target.profile_type,
                )
            )
            if existing:
                existing.overlap_reason = target.overlap_reason
                existing.priority_score = target.priority_score
                continue

            db.add(
                TargetKeyword(
                    business_input=business_input,
                    keyword=target.keyword,
                    profile_type=target.profile_type,
                    overlap_reason=target.overlap_reason,
                    priority_score=target.priority_score,
                )
            )
        db.commit()
