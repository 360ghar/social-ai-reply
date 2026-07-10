"""Instagram Graph API publishing client.

``InstagramPublisher`` posts a single image/caption or carousel to an
Instagram Business account via the Instagram Graph API (``POST /me/media``
+ ``POST /me/media_publish``). ``get_instagram_token`` retrieves the
workspace's stored token from ``integration_secrets`` (provider
``"instagram"``) and decrypts it.

.. note::

   The Instagram Graph API requires:
   * An Instagram Business or Creator account connected to a Facebook Page.
   * A Facebook Page access token with the ``instagram_basic``,
     ``instagram_content_publish``, and ``pages_read_engagement`` permissions.
   * The ``media_url`` parameter is **required** for image/video posts.
     For captions-only fallback this is a TODO once the media upload
     pipeline is in place.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

import httpx

from app.core.config import get_settings
from app.services.infrastructure.platform_token_utils import (
    get_platform_secret_value,
    get_platform_token,
)

if TYPE_CHECKING:
    from supabase import Client

logger = logging.getLogger(__name__)

IG_GRAPH_API_VERSION = "v22.0"
IG_GRAPH_BASE_URL = f"https://graph.facebook.com/{IG_GRAPH_API_VERSION}"
_REQUEST_TIMEOUT_SECONDS = 30.0
_PUBLISH_POLL_SLEEP = 2.0
_PUBLISH_POLL_MAX = 5


def get_instagram_token(db: Client, workspace_id: int) -> str | None:
    """Return the decrypted Instagram Graph API access token for a workspace,
    or None if not configured.

    Looks for an integration secret with provider ``"instagram"``.
    """
    return get_platform_token(db, workspace_id, "instagram")


def get_instagram_business_account_id(db: Client, workspace_id: int) -> str | None:
    """Return the Instagram Business Account ID for a workspace, or None.

    Stored as an integration secret with provider ``"instagram"`` and
    label ``"business_account_id"``.
    """
    return get_platform_secret_value(db, workspace_id, "instagram", "business_account_id")


class InstagramPublisher:
    """Instagram Graph API client for publishing content.

    Uses the two-step media creation flow:
    1. ``POST /{ig-user-id}/media``  — create a media container.
    2. ``POST /{ig-user-id}/media_publish`` — publish the container.

    Media containers can be:
    * IMAGE — requires ``image_url``.
    * CAROUSEL — requires multiple ``image_url`` values.
    * VIDEO — requires ``video_url``.

    For now only IMAGE is implemented; the caller can pass ``media_url``.
    A future TODO is uploading images from a URL to a temporary location
    when the media URL is not directly accessible.
    """

    def __init__(
        self,
        token: str,
        business_account_id: str,
        base_url: str = IG_GRAPH_BASE_URL,
    ) -> None:
        """Args:
        token: Facebook Page access token (string).
        business_account_id: Instagram Business Account ID (IG User ID).
        base_url: Facebook Graph API base URL (overridable for tests).
        """
        self._token = token
        self._business_account_id = business_account_id
        self._base_url = base_url

    # ── Public API ──────────────────────────────────────────────────────

    def publish_post(
        self,
        content: str,
        media_url: str | None = None,
    ) -> dict[str, Any]:
        """Publish a single Instagram post (image with caption).

        Args:
            content: Caption text for the post.
            media_url: Publicly accessible URL of an image to attach.
                       Required for standard feed posts.

        Returns:
            Dict with keys ``{"id": media_id}`` on success.

        Raises:
            RuntimeError: On API errors, network failures, or missing media_url.
        """
        if get_settings().mock_publishers:
            logger.info("[MOCK] Would publish to Instagram: %s", content)
            return {"id": "mock_ig_post"}

        if not media_url:
            raise RuntimeError(
                "Instagram standard feed posts require a media_url (image URL). "
                "Caption-only posts are not supported by the Instagram Graph API "
                "for feed publishing. Provide a media_url or implement a media "
                "upload pipeline."
            )

        # Step 1: create media container
        media_payload: dict[str, Any] = {
            "caption": content,
            "image_url": media_url,
            "media_type": "IMAGE",
        }

        container = self._create_media_container(media_payload)
        container_id = container.get("id")
        if not container_id:
            raise RuntimeError("Instagram API did not return a media container id.")

        # Step 2: poll for container status, then publish
        self._wait_for_container_ready(container_id)
        return self._publish_container(container_id)

    # ── Internal helpers ───────────────────────────────────────────────

    def _create_media_container(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST to /{ig-user-id}/media to create a media container."""
        url = f"{self._base_url}/{self._business_account_id}/media"
        return self._post(url, payload)

    def _wait_for_container_ready(self, container_id: str) -> None:
        """Poll GET /{container-id} until status is ``FINISHED``
        or we exceed the maximum number of polls.
        """
        url = f"{self._base_url}/{container_id}"
        for _attempt in range(_PUBLISH_POLL_MAX):
            result = self._get(url)
            status = result.get("status_code") if isinstance(result, dict) else ""
            if status == "FINISHED":
                return
            time.sleep(_PUBLISH_POLL_SLEEP)
        logger.warning(
            "Instagram media container %s did not reach FINISHED status "
            "within the poll window; attempting publish anyway.",
            container_id,
        )

    def _publish_container(self, container_id: str) -> dict[str, Any]:
        """POST to /{ig-user-id}/media_publish to publish the container."""
        url = f"{self._base_url}/{self._business_account_id}/media_publish"
        payload: dict[str, Any] = {"creation_id": container_id}
        response = self._post(url, payload)
        published_id = response.get("id")
        if not published_id:
            raise RuntimeError(
                "Instagram API did not return a published media id."
            )
        return {"id": published_id}

    # ── HTTP helpers ────────────────────────────────────────────────────

    def _post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST JSON with bearer auth, handling errors."""
        with httpx.Client(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            try:
                response = client.post(
                    url,
                    data={**payload, "access_token": self._token},
                )
            except httpx.HTTPError as exc:
                raise RuntimeError(f"Failed to reach Instagram Graph API: {exc}") from exc

        if response.status_code >= 400:
            detail = _extract_ig_error(response)
            raise RuntimeError(
                f"Instagram Graph API error (HTTP {response.status_code}): {detail}"
            )

        body = response.json()
        if isinstance(body, dict):
            if "error" in body:
                err = body["error"]
                raise RuntimeError(
                    f"Instagram Graph API error: {err.get('message', body)}"
                )
            return body
        raise RuntimeError(f"Instagram API returned unexpected response: {body}")

    def _get(self, url: str) -> dict[str, Any]:
        """GET with bearer auth."""
        with httpx.Client(timeout=_REQUEST_TIMEOUT_SECONDS) as client:
            try:
                response = client.get(url, params={"access_token": self._token})
            except httpx.HTTPError as exc:
                raise RuntimeError(f"Failed to reach Instagram Graph API: {exc}") from exc

        if response.status_code >= 400:
            detail = _extract_ig_error(response)
            raise RuntimeError(
                f"Instagram Graph API error (HTTP {response.status_code}): {detail}"
            )

        body = response.json()
        if isinstance(body, dict) and "error" in body:
            err = body["error"]
            raise RuntimeError(
                f"Instagram Graph API error: {err.get('message', body)}"
            )
        return body if isinstance(body, dict) else {}


def _extract_ig_error(response: httpx.Response) -> str:
    """Pull the most descriptive error message from an Instagram API response."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:500] or "no error detail"
    if isinstance(body, dict):
        err = body.get("error", {})
        if isinstance(err, dict):
            msg = err.get("message", "")
            code = err.get("code", "")
            subcode = err.get("error_subcode", "")
            parts = [p for p in (str(code), str(subcode), msg) if p]
            return " — ".join(parts)
        if body.get("error"):
            return str(body["error"])
        return str(body)[:500]
    return str(body)[:500]
