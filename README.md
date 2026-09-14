# mcp-google-search-console

A minimal, non-opinionated [Model Context Protocol](https://modelcontextprotocol.io/)
server for Google Search Console, by Bedupath. Python 3.11+ · stdio · MIT.

Read search performance, inspect Google's stored information for a URL, and manage
sitemap submissions. One service account can access multiple GSC properties.
Your agent's skills decide what to investigate; the server returns provider data
without SEO scores, strategy, automatic fixes, or workflow prompts.

## Documentation

- **[Setup and testing](docs/setup-and-testing.md)** — installation, Google credentials,
  client configuration, first live reads, safety checks, and troubleshooting.
- **[Use cases](docs/use-cases.md)** — concrete examples for indexing investigations,
  search performance, multiple properties, sitemaps, and external collectors.
- **[Tool and API reference](docs/reference.md)** — inputs, queries, responses,
  error semantics, provider limitations, and the reusable Python client.
- **[Contributing](CONTRIBUTING.md)** — development, branches, pull requests, and releases.

## Use cases

- Investigate a supplied URL's indexing state, crawl result, and canonical selection.
- Retrieve page/query performance or compare caller-selected reporting periods.
- Query multiple properties with one service account and an explicit property allowlist.
- Check sitemap processing warnings/errors and optionally manage submissions.
- Supply raw data to your own reports, agents, or scheduled Python collectors.

See [worked examples and their limits](docs/use-cases.md). The server does not choose
dates, discover every unindexed URL, schedule jobs, or store your reports.

## Install and connect

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then get the source:

```bash
git clone https://github.com/bedupath/mcp-google-search-console.git
cd mcp-google-search-console
uv sync --locked --no-dev
uv run --locked --no-dev mcp-google-search-console --version
```

You can also use an extracted source archive. These instructions install from source;
they do not require a published PyPI package. Repository access is required to clone.

Next, follow the [setup guide](docs/setup-and-testing.md) to create or reuse a Google
service account, grant GSC property access, and add the `google-search-console`
connection to your MCP client. It includes complete JSON and Codex TOML examples.
All paths and domains in the guides are placeholders, not working Google credentials
or properties.

No web server or public port is needed: your MCP host launches the stdio process.
The [optional offline checks](docs/setup-and-testing.md#3-optional-offline-verification)
need no Google account.

## Tools

| Tool | Purpose |
| --- | --- |
| `list_sites` | List accessible properties, filtered by the configured allowlist |
| `get_site` | Read one property's permission level |
| `query_search_analytics` | Query one page of Search Analytics rows |
| `inspect_url` | Retrieve Google's stored inspection result for a supplied URL |
| `list_sitemaps` | List submitted sitemap metadata |
| `get_sitemap` | Retrieve one submitted sitemap's metadata |
| `submit_sitemap` | Submit a sitemap URL; opt-in write |
| `delete_sitemap` | Remove a sitemap submission; opt-in write |

The default catalog has **six read-only tools**. The two sitemap writes are hidden
and blocked in the shared client unless `GSC_ENABLE_SITEMAP_WRITES=true`.
The [reference](docs/reference.md#tools) lists arguments and exact behavior.

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

## Important limits

URL inspection can explain Google's stored state for a **supplied URL**. It cannot
fetch the complete site-wide “Why pages aren't indexed” report, perform a live
inspection, or request indexing. Search Analytics returns limited top rows, not a
complete inventory of URLs. Sitemap submitted counts are not indexed counts.

See [API limits and result semantics](docs/reference.md#indexing-and-gsc-limitations).
An empty successful response, an unknown inspection state, and a failed API call
are different outcomes; the MCP keeps them distinct.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md) for offline checks and contribution scope, and
[SECURITY.md](SECURITY.md) for vulnerability reporting and its setup status. Never
share service-account keys, tokens, private URLs, or real analytics in public issues.

[AGENTS.md](AGENTS.md) and `.agents/skills/` are development guidance, not runtime
prompts. The package and documentation are not affiliated with Google.

Licensed under [MIT](LICENSE).
