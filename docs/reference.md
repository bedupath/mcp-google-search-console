# Tool and API reference

[Setup and testing](setup-and-testing.md) · [Use cases](use-cases.md) · [README](../README.md)

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

## Configuration

See the [environment-variable table](../README.md#configuration) for defaults and limits.
The [setup guide](setup-and-testing.md) includes complete client configurations.

## Search Analytics query

The `query` argument to `query_search_analytics` uses Google's native camelCase field names:

<!-- tool: query_search_analytics -->
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

Run this in the installed package's Python environment, with the same GSC variables
set in the script's environment. An MCP host's configured environment is not
automatically inherited by a separate terminal. Replace the example dates and property.

The caller owns dates, pagination, parallelism, storage, analysis, and any write
approval policy. `GSCError.as_dict()` exposes the same operational error fields.
Use the async context manager to close HTTP resources. A caller-injected HTTP
client remains caller-owned and must be closed by the caller.
