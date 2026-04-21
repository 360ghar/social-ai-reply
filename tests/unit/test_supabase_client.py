import httpx

from app.db.supabase_client import _force_http11_on_postgrest


class _FakePostgrest:
    def __init__(self) -> None:
        self.session = httpx.Client(
            base_url="https://example.supabase.co/rest/v1",
            headers={"apikey": "service-role"},
            timeout=10.0,
            http2=True,
        )


class _FakeSupabaseClient:
    def __init__(self) -> None:
        self.postgrest = _FakePostgrest()


def test_force_http11_on_postgrest_replaces_session_with_http11_client():
    client = _FakeSupabaseClient()
    original_session = client.postgrest.session

    try:
        _force_http11_on_postgrest(client)

        assert client.postgrest.session is not original_session
        assert client.postgrest.session._transport._pool._http2 is False
    finally:
        client.postgrest.session.close()
