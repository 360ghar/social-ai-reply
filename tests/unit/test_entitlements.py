"""Unit tests for plan entitlement limits behind the ENFORCE_PLAN_LIMITS flag."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services.product.entitlements import UNLIMITED, enforce_limit, get_limit

WORKSPACE = {"id": 1, "name": "Test"}


def _settings(enforce: bool) -> MagicMock:
    return MagicMock(enforce_plan_limits=enforce)


class TestFlagOff:
    def test_get_limit_unlimited(self):
        with patch("app.services.product.entitlements.get_settings", return_value=_settings(False)):
            assert get_limit(MagicMock(), WORKSPACE, "projects") == UNLIMITED

    def test_enforce_limit_noop_even_over_limit(self):
        with patch("app.services.product.entitlements.get_settings", return_value=_settings(False)):
            enforce_limit(MagicMock(), WORKSPACE, "projects", current_count=10_000_000)


class TestFlagOn:
    def _patches(self, *, subscription, entitlement):
        return (
            patch("app.services.product.entitlements.get_settings", return_value=_settings(True)),
            patch("app.services.product.entitlements.get_subscription_by_workspace", return_value=subscription),
            patch("app.services.product.entitlements.get_entitlement", return_value=entitlement),
        )

    def test_limit_from_entitlement_row(self):
        p1, p2, p3 = self._patches(
            subscription={"plan_code": "free"},
            entitlement={"plan_code": "free", "feature_key": "projects", "value": "3"},
        )
        with p1, p2, p3:
            assert get_limit(MagicMock(), WORKSPACE, "projects") == 3

    def test_falls_back_to_catalog_when_no_entitlement_row(self):
        p1, p2, p3 = self._patches(subscription={"plan_code": "free"}, entitlement=None)
        with p1, p2, p3:
            assert get_limit(MagicMock(), WORKSPACE, "projects") == UNLIMITED

    def test_unknown_plan_defaults_to_unlimited(self):
        p1, p2, p3 = self._patches(subscription={"plan_code": "legacy-pro"}, entitlement=None)
        with p1, p2, p3:
            assert get_limit(MagicMock(), WORKSPACE, "projects") == UNLIMITED

    def test_missing_subscription_treated_as_free(self):
        p1, p2, p3 = self._patches(subscription=None, entitlement=None)
        with p1, p2, p3:
            assert get_limit(MagicMock(), WORKSPACE, "projects") == UNLIMITED

    def test_non_numeric_entitlement_value_falls_back(self):
        p1, p2, p3 = self._patches(
            subscription={"plan_code": "free"},
            entitlement={"plan_code": "free", "feature_key": "projects", "value": "enabled"},
        )
        with p1, p2, p3:
            assert get_limit(MagicMock(), WORKSPACE, "projects") == UNLIMITED

    def test_enforce_limit_raises_402_at_limit(self):
        p1, p2, p3 = self._patches(
            subscription={"plan_code": "free"},
            entitlement={"plan_code": "free", "feature_key": "projects", "value": "3"},
        )
        with p1, p2, p3:
            with pytest.raises(HTTPException) as exc_info:
                enforce_limit(MagicMock(), WORKSPACE, "projects", current_count=3)
            assert exc_info.value.status_code == 402

    def test_enforce_limit_allows_below_limit(self):
        p1, p2, p3 = self._patches(
            subscription={"plan_code": "free"},
            entitlement={"plan_code": "free", "feature_key": "projects", "value": "3"},
        )
        with p1, p2, p3:
            enforce_limit(MagicMock(), WORKSPACE, "projects", current_count=2)
