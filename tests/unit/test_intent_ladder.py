"""Unit tests for the buying-stage intent ladder."""

from unittest.mock import MagicMock

from app.services.product.intent_ladder import (
    BUYING_STAGES,
    refine_stages_with_llm,
    stage_from_intent,
)


class TestStageFromIntent:
    def test_every_classifier_intent_maps_to_valid_stage(self):
        from app.services.product.intent_ladder import _INTENT_TO_STAGE

        for stage, confidence in _INTENT_TO_STAGE.values():
            assert stage in BUYING_STAGES
            assert 0.0 <= confidence <= 1.0

    def test_high_purchase_intents(self):
        assert stage_from_intent("looking_for_alternative")[0] == "ready_to_buy"
        assert stage_from_intent("comparison")[0] == "comparing"
        assert stage_from_intent("buyer_research")[0] == "evaluating"

    def test_unknown_or_missing_intent_defaults_to_unaware(self):
        assert stage_from_intent("something_new")[0] == "unaware"
        assert stage_from_intent(None)[0] == "unaware"


class TestRefineStagesWithLlm:
    def _llm(self, response):
        llm = MagicMock()
        llm.is_enabled = True
        llm.call_json.return_value = response
        return llm

    def test_parses_valid_response(self):
        llm = self._llm([
            {"index": 7, "stage": "ready_to_buy", "confidence": 0.9},
            {"index": 8, "stage": "comparing", "confidence": 0.8},
        ])
        items = [
            {"index": 7, "title": "t", "body": "b"},
            {"index": 8, "title": "t2", "body": "b2"},
        ]
        refined = refine_stages_with_llm(items, {"brand_name": "X"}, llm=llm)
        assert refined == {7: ("ready_to_buy", 0.9), 8: ("comparing", 0.8)}

    def test_invalid_stages_and_indices_dropped(self):
        llm = self._llm([
            {"index": 1, "stage": "buying_frenzy", "confidence": 0.9},
            {"index": "not-an-int", "stage": "comparing", "confidence": 0.8},
            {"index": 2, "stage": "evaluating", "confidence": 5.0},
        ])
        refined = refine_stages_with_llm([{"index": 1, "title": "t", "body": "b"}], None, llm=llm)
        assert refined == {2: ("evaluating", 1.0)}  # confidence clamped

    def test_llm_failure_returns_empty(self):
        llm = MagicMock()
        llm.is_enabled = True
        llm.call_json.side_effect = RuntimeError("provider down")
        assert refine_stages_with_llm([{"index": 1, "title": "t", "body": "b"}], None, llm=llm) == {}

    def test_disabled_llm_returns_empty(self):
        llm = MagicMock()
        llm.is_enabled = False
        assert refine_stages_with_llm([{"index": 1, "title": "t", "body": "b"}], None, llm=llm) == {}
        llm.call_json.assert_not_called()

    def test_empty_items_short_circuits(self):
        assert refine_stages_with_llm([], None) == {}

    def test_batches_large_inputs(self):
        llm = self._llm([])
        items = [{"index": i, "title": "t", "body": "b"} for i in range(25)]
        refine_stages_with_llm(items, None, llm=llm)
        assert llm.call_json.call_count == 3  # 25 items / batch size 10
