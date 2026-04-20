"""Unit tests for website analysis fetch behavior."""

import httpx

from app.services.product.copilot import analyzer as analyzer_module


class _FakeResponse:
    def __init__(self, url: str, text: str, status_code: int = 200):
        self.url = url
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("GET", self.url)
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("request failed", request=request, response=response)


def test_fetch_html_falls_back_to_http_after_https_failures(monkeypatch):
    attempts: list[tuple[str, bool]] = []
    outcomes = {
        ("https://example.com", True): httpx.ConnectError(
            "TLS handshake failed",
            request=httpx.Request("GET", "https://example.com"),
        ),
        ("https://example.com", False): httpx.ConnectError(
            "Connection still failed",
            request=httpx.Request("GET", "https://example.com"),
        ),
        ("http://example.com", True): _FakeResponse("http://example.com", "<html>ok</html>"),
    }

    class FakeClient:
        def __init__(self, *args, verify: bool = True, **kwargs):
            del args, kwargs
            self.verify = verify

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            del exc_type, exc, tb
            return False

        def get(self, url: str, headers: dict[str, str]):
            del headers
            attempts.append((url, self.verify))
            outcome = outcomes[(url, self.verify)]
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

    monkeypatch.setattr(analyzer_module.httpx, "Client", FakeClient)

    analyzer = analyzer_module.WebsiteAnalyzer.__new__(analyzer_module.WebsiteAnalyzer)
    html = analyzer._fetch_html("https://example.com")

    assert html == "<html>ok</html>"
    assert attempts == [
        ("https://example.com", True),
        ("https://example.com", False),
        ("http://example.com", True),
    ]


def test_analyze_website_uses_heuristics_when_llm_returns_no_structured_output(monkeypatch):
    html = """
    <html>
      <head>
        <title>360Ghar</title>
        <meta name="description" content="Property discovery and verification platform for home buyers and investors.">
      </head>
      <body>
        <h1>Find verified homes faster</h1>
        <p>Browse listings, compare neighborhoods, and schedule visits with practical support.</p>
      </body>
    </html>
    """

    monkeypatch.setattr(analyzer_module.WebsiteAnalyzer, "_fetch_html", lambda self, url: html)
    monkeypatch.setattr(analyzer_module, "_structured_brand_analysis", lambda llm, text, fallback_name: None)

    analyzer = analyzer_module.WebsiteAnalyzer()
    result = analyzer.analyze_website("https://www.360ghar.com")

    assert result.brand_name == "360Ghar"
    assert "Property discovery and verification platform" in result.summary
    assert result.product_summary
    assert result.target_audience
    assert result.call_to_action
    assert result.voice_notes == "Helpful, grounded, and specific."
    assert result.business_domain
