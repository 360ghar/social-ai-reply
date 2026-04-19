"""Placeholder for future discovery-table refactor tests.

These tests originally exercised helper functions (`_normalize_opportunity_record`,
`_prepare_opportunity_payload`) that were part of an unfinished opportunity
normalization refactor. The refactor was reverted before this branch was pushed,
so the tests are skipped until the refactor is re-introduced.
"""

import pytest

pytest.skip(
    "Skipped: depends on opportunity normalization refactor that is not yet on this branch.",
    allow_module_level=True,
)
