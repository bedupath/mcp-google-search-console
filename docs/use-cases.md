# Use cases

[README](../README.md) · [Setup and testing](setup-and-testing.md) · [Reference](reference.md)

These are optional examples of what a caller can do with the provider tools, not
instructions embedded in the MCP. Your agent, skills, or application decide what
to investigate and how to interpret results. There are no bundled SEO workflows,
scores, recommendations, or automated fixes.

Complete the [read-only setup](setup-and-testing.md) first. Replace example domains,
property identifiers, and dates with authorized values. Dates below are illustrative,
not rolling defaults. Tool arguments use JSON; successful results are raw Google objects.

## Investigate a known page's indexing status

Use `inspect_url` when you already know the URL you want to check:

<!-- tool: inspect_url -->
```json
{
  "site_url": "sc-domain:example.com",
  "inspection_url": "https://example.com/articles/getting-started/",
  "language_code": "en-US"
}
```

Look in `inspectionResult.indexStatusResult` for the fields Google returns, such as
`coverageState`, `verdict`, `robotsTxtState`, `pageFetchState`, `lastCrawlTime`,
`googleCanonical`, and `userCanonical`. Rich-result details may also be present
under `inspectionResult.richResultsResult`. Absent fields are not negative verdicts.

This can expose a reported reason for a supplied page not being indexed. It does
not discover every excluded URL or reproduce the site-wide “Why pages aren't
indexed” report. It also cannot test the live page, edit robots rules, or request
indexing. See the [indexing limitations](reference.md#indexing-and-gsc-limitations).
For a list of known URLs, the caller makes separate requests and manages quotas.

## See which searches bring traffic to a section

Use `query_search_analytics` to request query/page pairs for an explicitly chosen
period and section:

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
        "dimension": "page",
        "operator": "contains",
        "expression": "https://example.com/articles/"
      }]
    }],
    "dataState": "final",
    "rowLimit": 25,
    "startRow": 0
  }
}
```

Each returned row's `keys` follow the requested dimension order: query, then page.
Metrics include clicks, impressions, CTR, and position when Google supplies them.
The MCP does not classify keywords or prioritize content changes.

Request another page by changing `startRow` to `25` while keeping other inputs the
same. Pagination is caller-controlled, and Google's limits and privacy filtering
still apply. Missing rows do not prove that a page is unindexed or has no traffic.

## Compare periods or device segments

Request a daily device breakdown with `query_search_analytics`:

<!-- tool: query_search_analytics -->
```json
{
  "site_url": "sc-domain:example.com",
  "query": {
    "startDate": "2026-08-01",
    "endDate": "2026-08-07",
    "dimensions": ["date", "device"],
    "type": "web",
    "dataState": "final",
    "rowLimit": 100,
    "startRow": 0
  }
}
```

For a second period, repeat with `startDate: "2026-08-08"` and
`endDate: "2026-08-14"`, preserving the other settings. Your application or agent
aligns rows and calculates comparisons. The server does not choose periods, join
results, detect anomalies, or infer why a metric changed. Comparisons need consistent
filters and aggregation; CTR and position are not additive metrics.

## Access several properties from one connection

Grant the same service-account email access to each property, then set the process
allowlist to both exact identifiers. For example, the environment value can be:

```text
GSC_ALLOWED_SITES=["sc-domain:example.com","sc-domain:example.org"]
```

This shows the value, not a shell command. Encode it as a string inside your MCP
client's environment configuration, as in the [setup examples](setup-and-testing.md#5-configure-your-mcp-client).

Call `list_sites` to see accessible, allowed properties:

<!-- tool: list_sites -->
```json
{}
```

Then pass the chosen exact `site_url` to each operation. Results are not merged
across properties. This release supports one service-account identity per process,
not an OAuth account registry or automatic credential switching. If separate
identities are required, configure separate MCP entries/processes, each with its
own credentials and allowlist. Only grant each identity the access it needs.

## Check and manage sitemap submissions

Start with `list_sitemaps`, then use a returned sitemap's `path` in `get_sitemap`:

<!-- tool: get_sitemap -->
```json
{
  "site_url": "sc-domain:example.com",
  "feedpath": "https://example.com/sitemap.xml"
}
```

The result can contain processing state, warnings, errors, and submission/download
timestamps. It is metadata, not the hosted XML or a list of indexed pages.

If you intentionally want to submit a sitemap that is already hosted, first follow
the [write opt-in instructions](setup-and-testing.md#8-optional-sitemap-writes).
Authorize the exact property and URL, then call `submit_sitemap`:

<!-- tool: submit_sitemap -->
```json
{
  "site_url": "sc-domain:example.com",
  "feedpath": "https://example.com/sitemap.xml"
}
```

For a submission you intentionally want to remove, separately authorize the target
and call `delete_sitemap` with its exact URL:

<!-- tool: delete_sitemap -->
```json
{
  "site_url": "sc-domain:example.com",
  "feedpath": "https://example.com/sitemap.xml"
}
```

These are independent operations, not a submit-then-delete test sequence. An empty
success object means Google accepted the operation, not that pages are indexed.
Deletion removes the GSC submission; it does not delete the hosted XML or deindex
pages. On an ambiguous write error, inspect current state before retrying. The MCP
does not generate, upload, edit, or crawl sitemap files.

## Reuse the client in another project

A reporting script or collector can use the same async Python client without an
MCP host; see the [Python example](reference.md#reuse-without-mcp). Your application
owns scheduling, storage, retention, pagination, and analysis. No database, scheduler,
or consumer-specific strategy is built into this package. Keep property data and
credentials outside public repositories and apply your own access controls.
