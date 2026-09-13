"""Eight provider tools over stdio. No prompts, resources, or SEO workflow instructions."""

import argparse
import json
import logging
import sys
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

from . import __version__
from .client import GSCClient
from .config import Settings
from .errors import GSCError
from .models import HTTPURL, SearchAnalyticsQuery, SiteURL


async def _result(operation: Awaitable[dict[str, Any]]) -> CallToolResult:
    try:
        data = await operation
        is_error = False
    except GSCError as error:
        data = {"error": error.as_dict()}
        is_error = True
    return CallToolResult(
        content=[
            TextContent(type="text", text=json.dumps(data, ensure_ascii=False, allow_nan=False))
        ],
        structured_content=data,
        is_error=is_error,
    )


def create_server(
    settings: Settings | None = None,
    *,
    client_factory: Callable[[], GSCClient] | None = None,
) -> MCPServer[GSCClient]:
    config = settings if settings is not None else Settings.from_env()

    @asynccontextmanager
    async def lifespan(server: MCPServer[GSCClient]) -> AsyncIterator[GSCClient]:
        async with client_factory() if client_factory else GSCClient(config) as client:
            # A test/embedding factory must not change the advertised permission boundary.
            if client.settings != config:
                raise ValueError("Client settings must match server settings")
            yield client

    server = MCPServer(
        "mcp-google-search-console",
        version=__version__,
        lifespan=lifespan,
        log_level="WARNING",
    )
    read = ToolAnnotations(read_only_hint=True, open_world_hint=True)

    @server.tool(annotations=read)
    async def list_sites(ctx: Context[GSCClient]) -> CallToolResult:
        """List accessible GSC properties and permissions; filter by GSC_ALLOWED_SITES if set."""
        return await _result(ctx.request_context.lifespan_context.list_sites())

    @server.tool(annotations=read)
    async def get_site(site_url: SiteURL, ctx: Context[GSCClient]) -> CallToolResult:
        """Get one exact GSC property and its permission level (sc-domain: or URL-prefix)."""
        return await _result(ctx.request_context.lifespan_context.get_site(site_url))

    @server.tool(annotations=read)
    async def query_search_analytics(
        site_url: SiteURL, query: SearchAnalyticsQuery, ctx: Context[GSCClient]
    ) -> CallToolResult:
        """Query one Search Analytics page. Dates are inclusive Pacific dates; startRow pages
        Google's available top rows, not an exhaustive URL inventory. Returns raw rows/metadata.
        """
        return await _result(
            ctx.request_context.lifespan_context.query_search_analytics(site_url, query)
        )

    @server.tool(annotations=read)
    async def inspect_url(
        site_url: SiteURL,
        inspection_url: HTTPURL,
        ctx: Context[GSCClient],
        language_code: Annotated[str, Field(min_length=1, max_length=64)] | None = None,
    ) -> CallToolResult:
        """Get Google's stored URL inspection: indexing, crawl, canonicals, and rich results
        when available. Not a live test, site-wide coverage report, or indexing request.
        """
        return await _result(
            ctx.request_context.lifespan_context.inspect_url(
                site_url, inspection_url, language_code
            )
        )

    @server.tool(annotations=read)
    async def list_sitemaps(
        site_url: SiteURL, ctx: Context[GSCClient], sitemap_index: HTTPURL | None = None
    ) -> CallToolResult:
        """List submitted sitemap metadata, optionally under one sitemap index. Not URL contents."""
        return await _result(
            ctx.request_context.lifespan_context.list_sitemaps(site_url, sitemap_index)
        )

    @server.tool(annotations=read)
    async def get_sitemap(
        site_url: SiteURL, feedpath: HTTPURL, ctx: Context[GSCClient]
    ) -> CallToolResult:
        """Get sitemap metadata, warnings, and errors. Submitted counts are not indexed counts."""
        return await _result(ctx.request_context.lifespan_context.get_sitemap(site_url, feedpath))

    if config.enable_sitemap_writes:

        @server.tool(
            annotations=ToolAnnotations(
                read_only_hint=False,
                destructive_hint=False,
                idempotent_hint=True,
                open_world_hint=True,
            )
        )
        async def submit_sitemap(
            site_url: SiteURL, feedpath: HTTPURL, ctx: Context[GSCClient]
        ) -> CallToolResult:
            """Submit a sitemap URL to the exact GSC property. Does not create its file or guarantee
            indexing. Empty success is {}; a transport failure can leave the outcome unknown.
            """
            return await _result(
                ctx.request_context.lifespan_context.submit_sitemap(site_url, feedpath)
            )

        @server.tool(
            annotations=ToolAnnotations(
                read_only_hint=False,
                destructive_hint=True,
                idempotent_hint=True,
                open_world_hint=True,
            )
        )
        async def delete_sitemap(
            site_url: SiteURL, feedpath: HTTPURL, ctx: Context[GSCClient]
        ) -> CallToolResult:
            """Remove a sitemap submission from GSC; the hosted file and indexed pages remain.
            Empty success is {}; a transport failure can leave the outcome unknown.
            """
            return await _result(
                ctx.request_context.lifespan_context.delete_sitemap(site_url, feedpath)
            )

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Google Search Console MCP server (stdio)")
    parser.add_argument("--version", action="version", version=__version__)
    parser.parse_args()
    # Stdout is reserved for MCP. Provider URLs, payloads and credentials are not logged.
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    for name in ("httpx", "httpcore", "google.auth"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    try:
        create_server().run(transport="stdio")
    except GSCError as error:
        print(f"{error.code}: {error}", file=sys.stderr)
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
