"""Unified client for Agent-Reach CLI tools.

Wraps subprocess calls to rdt-cli, twitter-cli, and Jina Reader with
rate limiting, timeout handling, and graceful degradation when a tool
is not installed.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 30.0
_MIN_INTERVAL = 1.0  # seconds between calls to the same CLI tool


class AgentReachClient:
    """Unified client for Agent-Reach CLI tools.

    Each method:
    - Returns parsed JSON data on success
    - Returns None when the tool is not installed or the call fails
    - Logs warnings on failures (never raises for missing tools)
    """

    _tool_available: dict[str, bool | None] = {}

    def __init__(self) -> None:
        settings = get_settings()
        self._enabled = getattr(settings, "agent_reach_enabled", True)
        self._rdt_path = getattr(settings, "rdt_cli_path", "rdt")
        self._twitter_path = "twitter"
        self._last_call_time: dict[str, float] = {}
        self._timeout = _DEFAULT_TIMEOUT
        self._tool_available = {}

    def _is_tool_available(self, tool_name: str) -> bool:
        cached = self._tool_available.get(tool_name)
        if cached is not None:
            return cached
        available = shutil.which(tool_name) is not None
        self._tool_available[tool_name] = available
        if not available:
            logger.info("Agent-Reach tool %r not found on PATH", tool_name)
        return available

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def rdt_available(self) -> bool:
        return self._enabled and self._is_tool_available(self._rdt_path)

    @property
    def twitter_available(self) -> bool:
        return self._enabled and self._is_tool_available(self._twitter_path)

    # ── Reddit (rdt-cli) ──────────────────────────────────────────────

    def rdt_search(
        self,
        query: str,
        *,
        subreddit: str | None = None,
        sort: str = "relevance",
        time_filter: str = "week",
        limit: int = 20,
    ) -> list[dict[str, Any]] | None:
        """Search Reddit posts via rdt-cli.

        Returns a list of post dicts from the rdt JSON output, or None
        if rdt is unavailable or the search fails.
        """
        if not self.rdt_available:
            return None

        cmd = [self._rdt_path, "search", query, "--json", "-n", str(limit), "--sort", sort, "--time", time_filter]
        if subreddit:
            cmd.extend(["-r", subreddit])

        result = self._run(cmd, tool="rdt")
        if result is None:
            return None

        # rdt search --json returns {"ok": true, "data": {"data": {"children": [...]}}}
        try:
            if not result.get("ok"):
                logger.warning("rdt search returned ok=false: %s", result.get("error", ""))
                return None
            children = (
                result.get("data", {})
                .get("data", {})
                .get("children", [])
            )
            return [child.get("data", {}) for child in children if child.get("data")]
        except (AttributeError, TypeError):
            logger.warning("Unexpected rdt search output structure")
            return None

    def rdt_read(self, post_id: str, *, limit_comments: int = 10) -> dict[str, Any] | None:
        """Read a Reddit post and its comments via rdt-cli.

        Returns the full post dict with comments, or None on failure.
        """
        if not self.rdt_available:
            return None

        cmd = [self._rdt_path, "read", post_id, "--json", "-n", str(limit_comments)]
        return self._run(cmd, tool="rdt")

    # ── Twitter (twitter-cli) ─────────────────────────────────────────

    def twitter_search(
        self,
        query: str,
        *,
        search_type: str = "top",
        limit: int = 20,
    ) -> list[dict[str, Any]] | None:
        """Search tweets via twitter-cli.

        Returns a list of tweet dicts, or None if twitter-cli is
        unavailable or the search fails.
        """
        if not self.twitter_available:
            return None

        cmd = [
            self._twitter_path, "search", query,
            "--json",
            "-t", search_type,
            "-n", str(limit),
        ]
        result = self._run(cmd, tool="twitter")
        if result is None:
            return None

        try:
            if not result.get("ok"):
                logger.warning("twitter search returned ok=false: %s", result.get("error", ""))
                return None
            data = result.get("data", [])
            if isinstance(data, list):
                return data
            return None
        except (AttributeError, TypeError):
            logger.warning("Unexpected twitter search output structure")
            return None

    def twitter_read(self, tweet_id: str) -> dict[str, Any] | None:
        """Read a single tweet by ID via twitter-cli show command."""
        if not self.twitter_available:
            return None
        cmd = [self._twitter_path, "show", tweet_id, "--json"]
        return self._run(cmd, tool="twitter")

    # ── Jina Reader (web page to markdown) ─────────────────────────────

    def jina_read(self, url: str) -> str | None:
        """Read any web page as clean markdown via Jina Reader.

        Uses the public https://r.jina.ai/ endpoint — no API key needed.
        Returns the markdown text, or None on failure.
        """
        try:
            import httpx

            jina_url = f"https://r.jina.ai/{url}"
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.get(jina_url, headers={"Accept": "text/plain"})
                resp.raise_for_status()
                return resp.text
        except Exception as exc:
            logger.debug("Jina Reader failed for %s: %s", url, exc)
            return None

    # ── Internal helpers ───────────────────────────────────────────────

    def _run(self, cmd: list[str], *, tool: str) -> dict[str, Any] | None:
        """Execute a CLI command and return parsed JSON output.

        Handles rate limiting, timeouts, and common error patterns.
        Returns None on any failure (never raises).
        """
        self._throttle(tool)
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            self._last_call_time[tool] = time.monotonic()
        except FileNotFoundError:
            logger.warning("Tool %r not found at %r", tool, cmd[0])
            self._tool_available[cmd[0]] = False
            return None
        except subprocess.TimeoutExpired:
            logger.warning("Tool %r timed out after %ss", tool, self._timeout)
            return None
        except Exception as exc:
            logger.warning("Tool %r unexpected error: %s", tool, exc)
            return None

        if proc.returncode != 0:
            stderr = proc.stderr.strip()[:500] if proc.stderr else ""
            logger.warning("Tool %r exited %d: %s", tool, proc.returncode, stderr)
            return None

        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            logger.warning("Tool %r returned non-JSON output", tool)
            return None

    def _throttle(self, tool: str) -> None:
        """Enforce minimum interval between calls to the same tool."""
        last = self._last_call_time.get(tool, 0.0)
        elapsed = time.monotonic() - last
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)
