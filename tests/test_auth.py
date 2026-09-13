import asyncio
import json
import time
from urllib.parse import parse_qs

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from google.auth.exceptions import TransportError

from mcp_google_search_console.auth import TOKEN_URL, ServiceAccountAuth, _RefreshRequest
from mcp_google_search_console.config import READONLY_SCOPE, WRITE_SCOPE, Settings
from mcp_google_search_console.errors import GSCError


@pytest.fixture(scope="module")
def synthetic_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def credentials_file(tmp_path, synthetic_key):
    info = {
        "type": "service_account",
        "project_id": "synthetic-project",
        "private_key_id": "synthetic-key-id",
        "private_key": synthetic_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode(),
        "client_email": "synthetic@synthetic-project.iam.gserviceaccount.com",
        "client_id": "1234567890",
        "token_uri": TOKEN_URL,
    }
    path = tmp_path / "synthetic.json"
    path.write_text(json.dumps(info))
    return path


@pytest.mark.parametrize("writes,scope", [(False, READONLY_SCOPE), (True, WRITE_SCOPE)])
async def test_real_google_auth_signing_refresh_scope_and_concurrent_cache(
    monkeypatch, credentials_file, synthetic_key, writes, scope
):
    requests = []
    real_client = httpx.Client

    def handler(request):
        requests.append(request)
        assert str(request.url) == TOKEN_URL
        fields = parse_qs(request.content.decode())
        assert fields["grant_type"] == ["urn:ietf:params:oauth:grant-type:jwt-bearer"]
        claims = jwt.decode(
            fields["assertion"][0],
            synthetic_key.public_key(),
            algorithms=["RS256"],
            audience=TOKEN_URL,
        )
        assert claims["scope"] == scope
        assert claims["iss"] == "synthetic@synthetic-project.iam.gserviceaccount.com"
        return httpx.Response(
            200,
            json={
                "access_token": "synthetic-access-token",
                "expires_in": 3600,
                "token_type": "Bearer",
            },
        )

    monkeypatch.setattr(
        httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)
    )
    auth = ServiceAccountAuth(
        Settings(credentials_file=credentials_file, enable_sitemap_writes=writes)
    )
    assert not requests
    assert (
        await asyncio.gather(*(auth.get_token() for _ in range(8)))
        == ["synthetic-access-token"] * 8
    )
    assert len(requests) == 1


async def test_missing_credentials_error():
    with pytest.raises(GSCError) as caught:
        await ServiceAccountAuth(Settings()).get_token()
    assert caught.value.code == "credentials_missing"


@pytest.mark.parametrize(
    "contents",
    [
        "invalid secret",
        "[]",
        '{"type":"authorized_user","refresh_token":"secret"}',
        '{"type":"service_account","token_uri":"https://evil.example/token","private_key":"secret"}',
    ],
)
async def test_invalid_credentials_sanitized_no_network(tmp_path, contents):
    path = tmp_path / "synthetic.json"
    path.write_text(contents)
    with pytest.raises(GSCError) as caught:
        await ServiceAccountAuth(Settings(credentials_file=path)).get_token()
    assert caught.value.code == "credentials_invalid"
    assert "secret" not in str(caught.value)
    assert str(path) not in str(caught.value)


async def test_refresh_failure_does_not_expose_response(monkeypatch, credentials_file):
    real_client = httpx.Client
    transport = httpx.MockTransport(
        lambda r: httpx.Response(
            400, json={"error": "invalid_grant", "error_description": "PRIVATE"}
        )
    )
    monkeypatch.setattr(httpx, "Client", lambda **kw: real_client(transport=transport, **kw))
    with pytest.raises(GSCError) as caught:
        await ServiceAccountAuth(Settings(credentials_file=credentials_file)).get_token()
    assert caught.value.code == "authentication_failed"
    assert "PRIVATE" not in str(caught.value)


@pytest.mark.parametrize("url,method", [("https://evil.example/token", "POST"), (TOKEN_URL, "GET")])
def test_token_transport_rejects_other_endpoints_and_methods(url, method):
    with pytest.raises(TransportError):
        _RefreshRequest(30)(url, method)


def test_refresh_retry_and_deadline_budget():
    transport = _RefreshRequest(30)
    transport.calls = 3
    with pytest.raises(TransportError):
        transport(TOKEN_URL, "POST")
    transport.calls = 0
    transport.deadline = time.monotonic() - 1
    with pytest.raises(TransportError):
        transport(TOKEN_URL, "POST")


@pytest.mark.parametrize("mode", ["oversized", "transport_failure", "redirect"])
async def test_refresh_transport_failure_is_safe(monkeypatch, credentials_file, mode):
    real_client = httpx.Client
    calls = []

    def handle(request):
        calls.append(request)
        if mode == "oversized":
            return httpx.Response(200, content=b"a" * (256 * 1024 + 1))
        if mode == "transport_failure":
            raise httpx.ConnectError("private endpoint details")
        return httpx.Response(302, headers={"Location": "https://evil.example/token"})

    monkeypatch.setattr(
        httpx, "Client", lambda **kw: real_client(transport=httpx.MockTransport(handle), **kw)
    )
    with pytest.raises(GSCError) as caught:
        await ServiceAccountAuth(Settings(credentials_file=credentials_file)).get_token()
    assert caught.value.code == "authentication_failed"
    assert "private endpoint" not in str(caught.value)
    assert len(calls) == 1
