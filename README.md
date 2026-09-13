# mcp-google-search-console

A minimal, non-opinionated [Model Context Protocol](https://modelcontextprotocol.io/)
server for Google Search Console, by Bedupath. Python 3.11+ · stdio · MIT.

Eight provider operations, raw Google responses, and one service account across
multiple properties. Your agent's skills decide what to investigate and what to
change. This server supplies the API access—not SEO strategy, scores, reports,
automatic remediation, or prompts.

## Tools

| Tool | Inputs | Behavior |
| --- | --- | --- |
| `list_sites` | None | Accessible properties and permissions; optionally allowlist-filtered |
| `get_site` | `site_url` | One property and permission level |
| `query_search_analytics` | `site_url`, `query` | One page of raw Search Analytics rows and metadata |
| `inspect_url` | `site_url`, `inspection_url`, optional `language_code` | Google's stored URL inspection result |
| `list_sitemaps` | `site_url`, optional `sitemap_index` | Submitted sitemap metadata, optionally within an index |
| `get_sitemap` | `site_url`, `feedpath` | One submitted sitemap's metadata |
| `submit_sitemap` | `site_url`, `feedpath` | Submit a sitemap URL; opt-in write |
| `delete_sitemap` | `site_url`, `feedpath` | Remove a sitemap submission; opt-in write |

The default tool catalog has six read-only tools. The two write tools appear only
when `GSC_ENABLE_SITEMAP_WRITES=true`. The shared Python client enforces the same
write restriction; hiding tools and MCP annotations are not the security boundary.

`site_url` is the exact GSC property identifier, such as `sc-domain:example.com`
or `https://example.com/blog/`. Properties are not inferred, normalized, or selected
automatically. `feedpath` is the full sitemap URL, not a local file path. A sitemap
on another host is allowed; Google determines whether the submission is valid.

## Install and connect

The following works from a local checkout; it does not assume a published PyPI
package or a public repository. Install [uv](https://docs.astral.sh/uv/) first.

```bash
cd /absolute/path/to/mcp-google-search-console
uv sync --locked --no-dev
uv run --locked --no-dev mcp-google-search-console --version
```

Alternatively install this checkout with `python -m pip install .` in your own
virtual environment. The distribution name is
`bedupath-mcp-google-search-console`; the command is `mcp-google-search-console`.

### Google setup

1. Enable the [Search Console API](https://console.cloud.google.com/apis/library/searchconsole.googleapis.com)
   in your Google Cloud project.
2. Create a service account and obtain its JSON key. Keep it **outside this
   repository**, readable only by the account running the MCP server.
3. In each existing GSC property, add the JSON file's `client_email` under
   **Settings → Users and permissions**. Use the least access appropriate for
   the operations; Full user access supports the intended read and sitemap workflows.
4. Set `GOOGLE_APPLICATION_CREDENTIALS` to the absolute JSON file path.

This is one Google identity with access to several properties, including properties
owned by different human Google accounts. It is not simultaneous OAuth sessions
for different identities. Separate credentials can be isolated in separate MCP
processes; an account registry and interactive OAuth are outside this release.

See Google's [service-account authentication](https://developers.google.com/identity/protocols/oauth2/service-account)
and [GSC permission documentation](https://support.google.com/webmasters/answer/7687615).
Adding the service account as a GSC user does not require granting it project-wide
Google Cloud Owner or Editor roles. This server does not add or verify properties.

### MCP client configuration

For clients using an `mcpServers` JSON configuration:

```json
{
  "mcpServers": {
    "google-search-console": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/mcp-google-search-console", "--locked", "--no-dev", "mcp-google-search-console"],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/absolute/private/path/google-key.json",
        "GSC_ALLOWED_SITES": "[\"sc-domain:example.com\",\"https://another.example/blog/\"]"
      }
    }
  }
}
```

Use an absolute path to `uv` if your desktop MCP host does not inherit your shell's
PATH. For an installed virtual environment, the command can instead be
`/absolute/path/to/venv/bin/mcp-google-search-console`, without `uv` arguments.

For Codex's TOML configuration:

```toml
[mcp_servers.google-search-console]
command = "uv"
args = ["run", "--directory", "/absolute/path/to/mcp-google-search-console", "--locked", "--no-dev", "mcp-google-search-console"]

[mcp_servers.google-search-console.env]
GOOGLE_APPLICATION_CREDENTIALS = "/absolute/private/path/google-key.json"
GSC_ALLOWED_SITES = '["sc-domain:example.com"]'
```

No HTTP listener is started. The MCP host launches the process and communicates
through stdin/stdout. Diagnostic logs go to stderr. Startup and tool discovery do
not read credentials or contact Google; authentication is lazy on the first API call.

### Optional sitemap writes

Add `GSC_ENABLE_SITEMAP_WRITES=true` to the MCP process environment and restart the
process. It will request Google's `webmasters` scope instead of
`webmasters.readonly`. Google's property permissions still apply.

The flag enables both sitemap tools for every allowed property. Use an exact
`GSC_ALLOWED_SITES` list and, when appropriate, a separate read/write MCP process
with narrower credentials. The flag is process configuration, not per-call human
approval. Configure approvals in your host/skills; the server does not direct them.

Submitting registers a sitemap URL—it does not generate/upload its file or
guarantee indexing. Deleting removes its GSC submission—it does not delete the
hosted file or remove pages from Google's index. Neither write is automatically
retried. Google's empty successful response becomes `{}`.

## Configuration

Only these environment variables are read. `.env` files are not loaded automatically.

| Variable | Default | Meaning |
| --- | --- | --- |
| `GOOGLE_APPLICATION_CREDENTIALS` | Unset | Absolute service-account JSON path; required for Google calls |
| `GSC_ALLOWED_SITES` | Unset | JSON array of exact property identifiers; unset allows all credential-accessible properties, `[]` allows none |
| `GSC_ENABLE_SITEMAP_WRITES` | `false` | `true` or `false` (case-insensitive); other values fail closed |
| `GSC_REQUEST_TIMEOUT_SECONDS` | `30` | Per-API-attempt total timeout; 1–120 seconds; also bounds token transport's refresh budget |
| `GSC_MAX_RETRIES` | `2` | Additional attempts for transient reads; 0–5, not applied to writes |
| `GSC_MAX_RESPONSE_BYTES` | `16777216` | Maximum decoded Google response bytes; at least 1024; oversized responses fail without partial success |

The allowlist filters `list_sites` and guards every property-specific operation
before authentication. An empty allowlist returns an empty site list without a
Google call. Malformed configuration prevents startup rather than widening access.

Credentials must be standard Google service-account JSON using
`https://oauth2.googleapis.com/token` and the Google APIs universe. Other credential
types, delegated-user login, metadata discovery, custom token endpoints, and
environment-configured HTTP proxies are not supported. TLS verification stays on;
redirects are not followed. No tokens are stored on disk by this package.

## Search Analytics query

The `query` object uses Google's native camelCase field names:

```json
{
  "site_url": "sc-domain:example.com",
  "query": {
    "startDate": "2026-08-01",
    "endDate": "2026-08-31",
    "dimensions": ["query", "page"],
    "type": "web",
    "dimensionFilterGroups": [{
      "groupType": "and",
      "filters": [{
        "dimension": "query",
        "operator": "includingRegex",
        "expression": "(?i)example|sample"
      }]
    }],
    "aggregationType": "auto",
    "dataState": "final",
    "rowLimit": 25000,
    "startRow": 0
  }
}
```

Only dates are required. Optional fields are omitted from the Google request when
not supplied, leaving Google's own defaults intact. No date window is chosen for you.

- Dimensions: `country`, `device`, `page`, `query`, `searchAppearance`, `date`, `hour`.
- Types: `web`, `image`, `video`, `news`, `discover`, `googleNews`.
- Operators: `equals`, `notEquals`, `contains`, `notContains`, `includingRegex`,
  `excludingRegex`; regex evaluation is Google's RE2, not Python's regex engine.
- Aggregation: `auto`, `byPage`, `byProperty`, `byNewsShowcasePanel`.
- Data states: `final`, `all`, `hourly_all`; for hourly breakdown use `hour` with
  `hourly_all`. Incomplete-data metadata is preserved.
- `rowLimit`: 1–25,000; `startRow`: any nonnegative integer. Pagination is explicit,
  one request per tool call; there is no hidden fetch-all or row aggregation.

Invalid fields, dates, duplicate grouping dimensions, unsupported filter groups,
and incompatible `byProperty` combinations are rejected. Google validates the
remaining specialized combinations. The server never rewrites a query to make it fit.

Dates are inclusive in `America/Los_Angeles`, not the server's local timezone.
Rows follow Google's ordering. Search Analytics returns top rows subject to its
limits and privacy filtering; paginating does **not** establish an exhaustive
inventory of indexed or unindexed URLs. See the [query API contract](https://developers.google.com/webmaster-tools/v1/searchanalytics/query).

## Indexing and GSC limitations

`inspect_url` exposes the stored `inspectionResult` as returned by Google, including
coverage/indexing state, robots state, crawl/fetch information, canonical URLs,
and nested rich-result issues when available. Unknown or absent fields stay unknown
or absent. Failed requests are errors, never “not indexed.”

The [URL Inspection API](https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect)
can provide reasons for a **supplied URL** not being indexed. It does not expose
the complete site-wide “Why pages aren't indexed” report or discover all excluded
URLs. There is no live inspection or request-indexing endpoint in this MCP.
Security Issues, Manual Actions, Links, and other GSC UI-only reports are not added
through scraping or invented APIs. Building a custom MCP does not remove those gaps.

[Sitemap metadata](https://developers.google.com/webmaster-tools/v1/sitemaps)
contains processing warnings/errors but is not a sitemap URL crawler. A submitted
URL count is not an indexed count; deprecated fields are preserved if Google sends
them, not repurposed. Quotas and data availability remain Google's constraints.

## Result and error contract

Successful results contain the same JSON object in MCP `structuredContent` and a
JSON text block. Provider fields are retained, including unfamiliar future fields.
The only result transformations are the configured `list_sites` filter and mapping
an empty successful sitemap-write body to `{}`. There is no success envelope,
opportunity score, derived indexing verdict, or synthesized pagination metadata.

Known operational errors use MCP `isError: true` and this shape:

```json
{
  "error": {
    "code": "permission_denied",
    "message": "Google denied access; check property access and API enablement.",
    "http_status": 403,
    "retryable": false,
    "outcome_unknown": false
  }
}
```

Codes distinguish configuration, missing/invalid credentials, authentication,
denied properties, disabled writes, invalid input/request, permission denial,
not found, quota limits, transport failures, oversized/invalid responses, and other
Google HTTP errors. Upstream error bodies and credential paths are not echoed.
Schema errors and unknown tools use the MCP SDK's error format, also with `isError`.

Transient reads retry with bounded backoff; numeric `Retry-After` values are honored
up to 30 seconds. Final errors remain visible after exhaustion. A failed write with
`outcome_unknown: true` may already have reached Google; it must not be treated as
confirmed failure or retried blindly. There is no background polling or quota store.

## Reuse without MCP

The client can be imported by collectors, scripts, and future projects. It does not
import the MCP server or require an agent. Python inputs accept snake_case as well
as their native Google aliases:

```python
import asyncio

from mcp_google_search_console.client import GSCClient
from mcp_google_search_console.config import Settings
from mcp_google_search_console.models import SearchAnalyticsQuery


async def main():
    async with GSCClient(Settings.from_env()) as client:
        result = await client.query_search_analytics(
            "sc-domain:example.com",
            SearchAnalyticsQuery(start_date="2026-08-01", end_date="2026-08-31"),
        )
        print(result)


asyncio.run(main())
```

The caller owns dates, pagination, parallelism, storage, analysis, and any write
approval policy. `GSCError.as_dict()` exposes the same operational error fields.
Use the async context manager to close HTTP resources. A caller-injected HTTP
client remains caller-owned and must be closed by the caller.

## Development

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov=mcp_google_search_console --cov-report=term-missing
uv build
```

Tests use synthetic RSA credentials, mocked Google HTTP, in-process MCP sessions,
and a real stdio subprocess with no configured credentials. They do not require
GSC access and do not submit/delete live sitemaps. Passing them is local verification,
not a claim that a particular Google property or MCP host has been live-validated.

See [AGENTS.md](AGENTS.md) for contributor-agent boundaries and `.agents/skills/`
for focused engineering, review, and verification skills. Those development files
are not runtime prompts and are not included in the Python wheel.

## Security and contributing

Keep keys and real GSC responses out of commits, issues, fixtures, and logs. The
ignore rules are a convenience, not a secret-scanning guarantee. Rotate a leaked
Google key even if its Git history is later removed. When sharing diagnostics,
include sanitized error codes and request structure, not tokens or private URLs.

For vulnerabilities, use the repository's private vulnerability reporting channel
if enabled; do not publish exploitable details or credentials in a public issue.
There is no hosted credential-handling service in this project.

Contributions should preserve the provider-only boundary, include offline regression
tests, and run the checks above. New APIs or breaking schemas should be discussed
before expanding the eight-tool surface. This project is not affiliated with Google.

Licensed under [MIT](LICENSE).
