"""Keep public examples usable without keys, private configuration, or network access."""

import json
import re
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlsplit

import httpx
from mcp import Client

from mcp_google_search_console.config import Settings
from mcp_google_search_console.server import create_server

ROOT = Path(__file__).resolve().parents[1]
PAGES = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
TOOL_EXAMPLE = re.compile(r"<!-- tool: (\w+) -->\s*```json\n(.*?)\n```", re.DOTALL)


def test_public_documentation_local_links_and_anchors():
    assert (ROOT / "docs" / "setup-and-testing.md") in PAGES
    assert (ROOT / "docs" / "use-cases.md") in PAGES
    assert (ROOT / "docs" / "reference.md") in PAGES
    for page in PAGES:
        for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", page.read_text()):
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc:
                continue
            target = (page.parent / unquote(parsed.path)).resolve() if parsed.path else page
            # Contributor-agent guidance is deliberately excluded from source archives.
            if target == ROOT / "AGENTS.md" and not (ROOT / ".agents").exists():
                continue
            assert target.is_file(), (page, link)
            if parsed.fragment:
                headings = re.findall(r"^#{1,6} (.+)$", target.read_text(), re.MULTILINE)
                anchors = {re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-") for h in headings}
                assert unquote(parsed.fragment) in anchors, (page, link)


async def test_documented_client_configurations_are_valid_and_read_only():
    configs = []
    for page in PAGES:
        for language, body in re.findall(
            r"```(json|toml)\n(.*?)\n```", page.read_text(), re.DOTALL
        ):
            parsed = json.loads(body) if language == "json" else tomllib.loads(body)
            if "mcpServers" in parsed:
                configs.append(parsed["mcpServers"]["google-search-console"])
            if "mcp_servers" in parsed:
                configs.append(parsed["mcp_servers"]["google-search-console"])
    assert len(configs) >= 2
    for config in configs:
        settings = Settings.from_env(config["env"])
        assert settings.credentials_file.is_absolute()
        assert settings.allowed_sites == frozenset({"sc-domain:example.com"})
        assert not settings.enable_sitemap_writes
        assert config["command"] == "uv"
        assert config["args"][-1] == "mcp-google-search-console"
        assert "--locked" in config["args"] and "--no-dev" in config["args"]
        async with Client(create_server(settings)) as client:
            names = {tool.name for tool in (await client.list_tools()).tools}
        assert len(names) == 6
        if "enabled_tools" in config:
            assert set(config["enabled_tools"]) == names


async def test_documented_tool_arguments_pass_protocol_validation(client_factory):
    # Validate inputs independently of property grants, including the denial-test
    # input. Authorization behavior is covered by the client/server tests.
    settings = Settings(enable_sitemap_writes=True)
    requests = []

    def handler(request):
        requests.append(request)
        return (
            httpx.Response(204)
            if request.method in {"PUT", "DELETE"}
            else httpx.Response(200, json={})
        )

    google, _, _ = client_factory(handler, settings)
    exercised = set()
    async with Client(create_server(settings, client_factory=lambda: google)) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
        for page in PAGES:
            for name, body in TOOL_EXAMPLE.findall(page.read_text()):
                assert name in names, (page, name)
                before = len(requests)
                result = await client.call_tool(name, json.loads(body))
                assert not result.is_error, (page, name, result.content)
                assert len(requests) == before + 1
                exercised.add(name)
    assert exercised == names
