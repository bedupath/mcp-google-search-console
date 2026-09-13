import asyncio
import json
from urllib.parse import quote

import httpx
import pytest

from mcp_google_search_console.client import API_ROOT, INSPECTION_URL
from mcp_google_search_console.config import Settings
from mcp_google_search_console.errors import GSCError
from mcp_google_search_console.models import SearchAnalyticsQuery

SITE = "sc-domain:example.com"
FEED = "https://cdn.example.net/sitemap.xml?lang=fr&section=books"


async def test_all_eight_operations_exact_provider_contract(client_factory):
    requests = []
    response = {"providerField": {"unknownFutureField": True}}

    def handle(request):
        requests.append(request)
        return (
            httpx.Response(204)
            if request.method in {"PUT", "DELETE"}
            else httpx.Response(200, json=response)
        )

    client, auth, delays = client_factory(handle, Settings(enable_sitemap_writes=True))
    assert await client.list_sites() == response
    assert await client.get_site(SITE) == response
    query = SearchAnalyticsQuery(
        startDate="2026-01-01",
        endDate="2026-01-31",
        dimensions=["query", "page", "country"],
        type="web",
        aggregationType="auto",
        dataState="all",
        rowLimit=25000,
        startRow=50000,
        dimensionFilterGroups=[
            {
                "groupType": "and",
                "filters": [
                    {
                        "dimension": "query",
                        "operator": "includingRegex",
                        "expression": "(?i)brand.*",
                    },
                    {"dimension": "page", "operator": "excludingRegex", "expression": "/private/"},
                ],
            }
        ],
    )
    assert await client.query_search_analytics(SITE, query) == response
    assert await client.inspect_url(SITE, "https://example.com/a?x=1", "en-US") == response
    assert await client.list_sitemaps(SITE, FEED) == response
    assert await client.get_sitemap(SITE, FEED) == response
    assert await client.submit_sitemap(SITE, FEED) == {}
    assert await client.delete_sitemap(SITE, FEED) == {}
    assert auth.calls == 8
    assert delays == []
    site_path = f"{API_ROOT}/sites/{quote(SITE, safe='')}"
    sitemap_path = f"{site_path}/sitemaps/{quote(FEED, safe='')}"
    assert [(r.method, str(r.url).split("?")[0]) for r in requests] == [
        ("GET", f"{API_ROOT}/sites"),
        ("GET", site_path),
        ("POST", f"{site_path}/searchAnalytics/query"),
        ("POST", INSPECTION_URL),
        ("GET", f"{site_path}/sitemaps"),
        ("GET", sitemap_path),
        ("PUT", sitemap_path),
        ("DELETE", sitemap_path),
    ]
    assert json.loads(requests[2].content) == query.model_dump(by_alias=True, exclude_none=True)
    assert json.loads(requests[3].content) == {
        "siteUrl": SITE,
        "inspectionUrl": "https://example.com/a?x=1",
        "languageCode": "en-US",
    }
    assert requests[4].url.params["sitemapIndex"] == FEED
    assert requests[6].content == requests[7].content == b""
    assert all(r.headers["Authorization"] == "Bearer synthetic-test-token" for r in requests)


async def test_url_prefix_fully_encoded_without_double_encoding(client_factory):
    seen = []
    client, _, _ = client_factory(lambda r: seen.append(r) or httpx.Response(200, json={}))
    await client.get_site("https://example.com/blog/")
    assert seen[0].url.raw_path == b"/webmasters/v3/sites/https%3A%2F%2Fexample.com%2Fblog%2F"


async def test_raw_indexing_and_sitemap_fields_not_reinterpreted(client_factory):
    response = {
        "inspectionResult": {
            "indexStatusResult": {
                "verdict": "VERDICT_UNSPECIFIED",
                "robotsTxtState": "DISALLOWED",
                "coverageState": "Blocked by robots.txt",
            },
            "richResultsResult": {
                "detectedItems": [
                    {
                        "items": [
                            {
                                "issues": [
                                    {"issueMessage": "Missing field", "severity": "ERROR"},
                                ]
                            }
                        ]
                    }
                ]
            },
        },
        "sitemap": [{"contents": [{"submitted": "12"}], "errors": "1"}],
        "metadata": {"first_incomplete_date": "2026-01-01"},
    }
    client, _, _ = client_factory(lambda r: httpx.Response(200, json=response))
    assert await client.inspect_url(SITE, "https://example.com/") == response
    assert await client.list_sitemaps(SITE) == response
    assert "not_indexed" not in json.dumps(response)
    assert "indexed_urls" not in json.dumps(response)


async def test_empty_success_stays_empty(client_factory):
    client, _, _ = client_factory(lambda r: httpx.Response(200, json={}))
    assert (
        await client.query_search_analytics(
            SITE, SearchAnalyticsQuery(startDate="2026-01-01", endDate="2026-01-02")
        )
        == {}
    )


async def test_allowlist_filters_sites_without_other_transformations(client_factory):
    response = {
        "siteEntry": [
            {"siteUrl": SITE, "permissionLevel": "siteFullUser"},
            {"siteUrl": "sc-domain:other.example", "permissionLevel": "siteOwner"},
        ],
        "future": "retained",
    }
    client, _, _ = client_factory(
        lambda r: httpx.Response(200, json=response), Settings(allowed_sites=frozenset({SITE}))
    )
    assert await client.list_sites() == {
        "siteEntry": [response["siteEntry"][0]],
        "future": "retained",
    }


@pytest.mark.parametrize(
    "operation",
    ["get_site", "query", "inspect", "list_sitemaps", "get_sitemap", "submit", "delete"],
)
async def test_denied_properties_never_authenticate_or_send(client_factory, operation):
    def forbidden(request):
        pytest.fail("No HTTP request should occur")

    client, auth, _ = client_factory(
        forbidden,
        Settings(allowed_sites=frozenset({"sc-domain:other.example"}), enable_sitemap_writes=True),
    )
    operations = {
        "get_site": lambda: client.get_site(SITE),
        "query": lambda: client.query_search_analytics(
            SITE, SearchAnalyticsQuery(startDate="2026-01-01", endDate="2026-01-02")
        ),
        "inspect": lambda: client.inspect_url(SITE, "https://example.com/"),
        "list_sitemaps": lambda: client.list_sitemaps(SITE),
        "get_sitemap": lambda: client.get_sitemap(SITE, FEED),
        "submit": lambda: client.submit_sitemap(SITE, FEED),
        "delete": lambda: client.delete_sitemap(SITE, FEED),
    }
    with pytest.raises(GSCError, match="not in GSC_ALLOWED_SITES"):
        await operations[operation]()
    assert auth.calls == 0


async def test_empty_allowlist_returns_no_sites_without_auth(client_factory):
    client, auth, _ = client_factory(
        lambda r: pytest.fail("Unexpected HTTP"), Settings(allowed_sites=frozenset())
    )
    assert await client.list_sites() == {"siteEntry": []}
    assert auth.calls == 0


@pytest.mark.parametrize("method", ["submit_sitemap", "delete_sitemap"])
async def test_writes_disabled_even_for_library_call(client_factory, method):
    client, auth, _ = client_factory(lambda r: pytest.fail("Unexpected HTTP"))
    with pytest.raises(GSCError) as caught:
        await getattr(client, method)(SITE, FEED)
    assert caught.value.code == "writes_disabled"
    assert auth.calls == 0


@pytest.mark.parametrize(
    "status,reason", [(429, None), (503, None), (403, "userRateLimitExceeded")]
)
async def test_read_retries_then_succeeds(client_factory, status, reason):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) < 3:
            return httpx.Response(
                status,
                headers={"Retry-After": "2"},
                json={
                    "error": {"message": "secret upstream message", "errors": [{"reason": reason}]}
                },
            )
        return httpx.Response(200, json={"siteUrl": SITE})

    client, _, delays = client_factory(handler)
    assert await client.get_site(SITE) == {"siteUrl": SITE}
    assert delays == [2, 2]


@pytest.mark.parametrize(
    "status,code",
    [
        (400, "invalid_request"),
        (401, "unauthorized"),
        (403, "permission_denied"),
        (404, "not_found"),
        (302, "google_api_error"),
    ],
)
async def test_permanent_errors_are_sanitized_and_not_retried(client_factory, status, code):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(
            status,
            headers={"Location": "https://evil.example/"},
            json={"error": {"message": "secret upstream payload"}},
        )

    client, _, delays = client_factory(handle)
    with pytest.raises(GSCError) as caught:
        await client.get_site(SITE)
    assert caught.value.code == code
    assert caught.value.http_status == status
    assert "secret" not in json.dumps(caught.value.as_dict())
    assert len(requests) == 1
    assert not delays


async def test_exhausted_read_transport_retry(client_factory):
    calls = []

    def fail(request):
        calls.append(request)
        raise httpx.ReadTimeout("secret upstream path", request=request)

    client, _, delays = client_factory(fail)
    with pytest.raises(GSCError) as caught:
        await client.get_site(SITE)
    assert caught.value.code == "transport_error"
    assert caught.value.retryable
    assert len(calls) == 3
    assert delays == [1, 2]
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("failure", ["timeout", "503"])
async def test_write_failures_never_retry_and_report_unknown_outcome(client_factory, failure):
    requests = []

    def handle(request):
        requests.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("sensitive", request=request)
        return httpx.Response(503, json={"error": "sensitive"})

    client, _, delays = client_factory(handle, Settings(enable_sitemap_writes=True))
    with pytest.raises(GSCError) as caught:
        await client.submit_sitemap(SITE, FEED)
    assert caught.value.outcome_unknown
    assert not caught.value.retryable
    assert len(requests) == 1
    assert delays == []


@pytest.mark.parametrize("body", [b"not json", b"[]", b"", b'{"x":NaN}', b"\xff"])
async def test_malformed_success_is_an_error_not_empty_data(client_factory, body):
    client, _, _ = client_factory(lambda r: httpx.Response(200, content=body))
    with pytest.raises(GSCError) as caught:
        await client.get_site(SITE)
    assert caught.value.code == "invalid_response"


async def test_response_limit_has_no_truncated_success(client_factory):
    client, _, _ = client_factory(
        lambda r: httpx.Response(200, content=b"a" * 1025), Settings(max_response_bytes=1024)
    )
    with pytest.raises(GSCError) as caught:
        await client.get_site(SITE)
    assert caught.value.code == "response_too_large"


async def test_cancelled_operation_is_not_retried(client_factory):
    def handle(request):
        raise asyncio.CancelledError

    client, _, delays = client_factory(handle)
    with pytest.raises(asyncio.CancelledError):
        await client.get_site(SITE)
    assert delays == []


@pytest.mark.parametrize("site_entries", [None, {}, [{"siteUrl": []}], ["bad entry"]])
async def test_malformed_filtered_site_list_is_a_safe_error(client_factory, site_entries):
    client, _, _ = client_factory(
        lambda r: httpx.Response(200, json={"siteEntry": site_entries}),
        Settings(allowed_sites=frozenset({SITE})),
    )
    with pytest.raises(GSCError) as caught:
        await client.list_sites()
    assert caught.value.code == "invalid_response"


@pytest.mark.parametrize("retry_after,expected", [("invalid", 1), ("99999", 30), ("-3", 1)])
async def test_retry_after_is_bounded(client_factory, retry_after, expected):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": retry_after}, json={})
        return httpx.Response(200, json={})

    client, _, delays = client_factory(handler)
    await client.get_site(SITE)
    assert delays == [expected]


async def test_api_attempt_has_total_deadline(client_factory):
    async def slow_handler(request):
        await asyncio.sleep(5)
        pytest.fail("Request should have been cancelled at the deadline")

    client, _, delays = client_factory(
        slow_handler, Settings(request_timeout_seconds=1, max_retries=0)
    )
    async with asyncio.timeout(3):
        with pytest.raises(GSCError) as caught:
            await client.get_site(SITE)
    assert caught.value.code == "transport_error"
    assert delays == []


async def test_owned_http_client_closed_by_context_manager():
    from mcp_google_search_console.client import GSCClient

    client = GSCClient(Settings())
    async with client:
        assert not client._http.is_closed
    assert client._http.is_closed


async def test_borrowed_http_client_not_closed_by_context_manager(client_factory):
    client, _, _ = client_factory(lambda r: httpx.Response(200, json={}))
    async with client:
        assert not client._http.is_closed
    assert not client._http.is_closed
