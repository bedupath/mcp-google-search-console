import asyncio
import json
import sys

import httpx
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from mcp_google_search_console.config import Settings
from mcp_google_search_console.server import create_server

READ_TOOLS = {
    "list_sites",
    "get_site",
    "query_search_analytics",
    "inspect_url",
    "list_sitemaps",
    "get_sitemap",
}
WRITE_TOOLS = {"submit_sitemap", "delete_sitemap"}
SITE = "sc-domain:example.com"


@pytest.mark.parametrize("writes", [False, True])
async def test_catalog_and_annotations_and_no_directions(client_factory, writes):
    settings = Settings(enable_sitemap_writes=writes)
    google, auth, _ = client_factory(lambda r: httpx.Response(200, json={}), settings)
    server = create_server(settings, client_factory=lambda: google)
    async with Client(server) as client:
        assert client.instructions is None
        tools = (await client.list_tools()).tools
        assert {t.name for t in tools} == READ_TOOLS | (WRITE_TOOLS if writes else set())
        assert not (await client.list_prompts()).prompts
        assert not (await client.list_resources()).resources
        assert not (await client.list_resource_templates()).resource_templates
        for tool in tools:
            assert "ctx" not in tool.input_schema["properties"]
            assert tool.annotations.read_only_hint == (tool.name in READ_TOOLS)
            if tool.name == "delete_sitemap":
                assert tool.annotations.destructive_hint
        assert auth.calls == 0


async def test_all_eight_tools_through_protocol(client_factory):
    settings = Settings(enable_sitemap_writes=True)
    seen = []

    def handler(request):
        seen.append(request)
        return (
            httpx.Response(204)
            if request.method in {"PUT", "DELETE"}
            else httpx.Response(200, json={"raw": [1, {"field": "value"}]})
        )

    google, _, _ = client_factory(handler, settings)
    async with Client(create_server(settings, client_factory=lambda: google)) as client:
        operations = {
            "list_sites": {},
            "get_site": {"site_url": SITE},
            "query_search_analytics": {
                "site_url": SITE,
                "query": {
                    "startDate": "2026-01-01",
                    "endDate": "2026-01-02",
                    "rowLimit": 25000,
                },
            },
            "inspect_url": {"site_url": SITE, "inspection_url": "https://example.com/"},
            "list_sitemaps": {"site_url": SITE},
            **{
                name: {"site_url": SITE, "feedpath": "https://example.com/sitemap.xml"}
                for name in {"get_sitemap", "submit_sitemap", "delete_sitemap"}
            },
        }
        for name, args in operations.items():
            result = await client.call_tool(name, args)
            assert not result.is_error, result.content
            expected = {} if name in WRITE_TOOLS else {"raw": [1, {"field": "value"}]}
            assert result.structured_content == expected
            assert json.loads(result.content[0].text) == expected
    assert len(seen) == 8


async def test_errors_have_is_error_and_structured_error_not_indexing_data(client_factory):
    google, _, _ = client_factory(
        lambda r: httpx.Response(403, json={"error": {"message": "PRIVATE"}})
    )
    async with Client(create_server(Settings(), client_factory=lambda: google)) as client:
        result = await client.call_tool(
            "inspect_url", {"site_url": SITE, "inspection_url": "https://example.com/"}
        )
        assert result.is_error
        assert result.structured_content["error"]["code"] == "permission_denied"
        assert "PRIVATE" not in str(result)
        assert "not_indexed" not in str(result)


async def test_unadvertised_write_cannot_be_invoked(client_factory):
    google, auth, _ = client_factory(lambda r: pytest.fail("Unexpected Google call"))
    async with Client(create_server(Settings(), client_factory=lambda: google)) as client:
        result = await client.call_tool(
            "delete_sitemap", {"site_url": SITE, "feedpath": "https://example.com/sitemap.xml"}
        )
        assert result.is_error
        assert auth.calls == 0


@pytest.mark.parametrize(
    "args",
    [
        {"site_url": SITE, "query": {"startDate": "bad", "endDate": "2026-01-02"}},
        {
            "site_url": SITE,
            "query": {"startDate": "2026-01-01", "endDate": "2026-01-02", "rowLimit": 25001},
        },
        {
            "site_url": SITE,
            "query": {"startDate": "2026-01-01", "endDate": "2026-01-02", "orderBy": []},
        },
        {
            "site_url": "ftp://example.com/",
            "query": {"startDate": "2026-01-01", "endDate": "2026-01-02"},
        },
    ],
)
async def test_invalid_tool_input_never_reaches_google(client_factory, args):
    google, auth, _ = client_factory(lambda r: pytest.fail("Unexpected Google call"))
    async with Client(create_server(Settings(), client_factory=lambda: google)) as client:
        result = await client.call_tool("query_search_analytics", args)
        assert result.is_error
        assert auth.calls == 0


@pytest.mark.parametrize("mode", ["auto", "legacy"])
async def test_stdio_subprocess_starts_and_returns_missing_credentials_without_network(mode):
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_google_search_console"],
        env={"GOOGLE_APPLICATION_CREDENTIALS": "", "GSC_ENABLE_SITEMAP_WRITES": "false"},
    )
    async with asyncio.timeout(15):
        async with Client(params, mode=mode) as client:
            assert {tool.name for tool in (await client.list_tools()).tools} == READ_TOOLS
            result = await client.call_tool("get_site", {"site_url": SITE})
            assert result.is_error
            assert result.structured_content["error"]["code"] == "credentials_missing"
