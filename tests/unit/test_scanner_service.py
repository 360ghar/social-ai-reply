"""Placeholder for future scanner refactor tests.

The original test in this module asserted error-handling behavior that depended
on an unfinished scanner refactor (`_hydrate_scan_run_response` and surrounding
scan-run updates). The refactor was reverted before this branch was pushed, so
the test is skipped until the refactor is re-introduced.
"""

import pytest

pytest.skip(
    "Skipped: depends on scanner refactor that is not yet on this branch.",
    allow_module_level=True,
)
