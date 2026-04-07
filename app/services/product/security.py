"""Security utilities — non-auth helpers.

Auth-related functions (password hashing, JWT creation/decoding) have been
removed as authentication is now handled by Supabase Auth. See
app/services/product/supabase_auth.py for the new auth integration.
"""

import ipaddress
import re
import socket
from urllib.parse import urlparse


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "workspace"


def validate_webhook_url(url: str) -> None:
    """Validate a webhook URL to prevent SSRF attacks."""
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP(S) URLs are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Only HTTP(S) URLs are allowed.")

    # Resolve hostname to IP addresses
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise ValueError("Only HTTP(S) URLs are allowed.") from exc

    for addr_info in addr_infos:
        ip = ipaddress.ip_address(addr_info[4][0])
        if not ip.is_global:
            raise ValueError("Internal URLs are not allowed.")
