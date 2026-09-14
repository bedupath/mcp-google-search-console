# Setup and testing

[README](../README.md) · [Use cases](use-cases.md) · [Reference](reference.md)

This guide takes a new installation from local checks to the first Google reads.
Start read-only; sitemap writes are optional. No previous MCP installation is needed.
The examples use the connection name `google-search-console`.

## Contents

- [1. Prerequisites](#1-prerequisites)
- [2. Install from source](#2-install-from-source)
- [3. Optional offline verification](#3-optional-offline-verification)
- [4. Set up Google access](#4-set-up-google-access)
- [5. Configure your MCP client](#5-configure-your-mcp-client)
- [6. Validate and connect](#6-validate-and-connect)
- [7. Test live reads and restrictions](#7-test-live-reads-and-restrictions)
- [8. Optional sitemap writes](#8-optional-sitemap-writes)
- [9. Troubleshooting and disabling the connection](#9-troubleshooting-and-disabling-the-connection)

## 1. Prerequisites

You need Python 3.11+, [uv](https://docs.astral.sh/uv/getting-started/installation/),
and an MCP client that supports local stdio servers. Git is needed only to clone
the source. For live reads, you also need a Google Cloud project, a service account,
and access to an existing Search Console property.

All `/absolute/...` paths, `example.com`/`example.org` domains, and sample dates below
are placeholders. Replace them before live use. Use your property's exact identifier:
`sc-domain:example.com` for a Domain property, or `https://example.com/blog/` for a
URL-prefix property. The server does not create or verify properties for you.

Shell examples use a POSIX shell. On Windows, adapt paths and use a shell that
supports the shown syntax, or save embedded Python snippets as `.py` files and run
them with `uv run --locked --no-dev python filename.py`. In JSON, Windows paths can
use forward slashes, for example `C:/private/google-key.json`.

## 2. Install from source

```bash
git clone https://github.com/bedupath/mcp-google-search-console.git
cd mcp-google-search-console
uv sync --locked --no-dev
uv run --locked --no-dev mcp-google-search-console --version
```

Alternatively, extract a source archive and run the last two commands from its
root. No PyPI release is assumed. If cloning requires authentication, you need
repository access; changing MCP settings will not solve a Git access problem.

Expected: the installed version prints and the command exits successfully.
This verifies installation, not Google authentication. Note the absolute path of
this checkout for the client configuration below.

Do not launch a separate HTTP service or open a port. The MCP client will start
the stdio process. Running the server manually without `--version` makes it wait
for protocol input; silence is not itself an error. Use Ctrl+C to stop it.

## 3. Optional offline verification

From the checkout root:

```bash
uv sync --locked
uv run --locked pytest -q
```

Expected: all tests pass, including mocked Google authentication and stdio protocol
checks. No key or property is needed, and no live sitemap is submitted or deleted.
The suite also checks the documented tool arguments against MCP schemas.

For lint, typing, and builds, see [contributor verification](../CONTRIBUTING.md#verification).
Passing offline checks is not evidence of live account access or successful indexing.

## 4. Set up Google access

1. In your Google Cloud project, enable the
   [Search Console API](https://console.cloud.google.com/apis/library/searchconsole.googleapis.com).
2. Create a service account, or reuse one you control. Creating one for this MCP
   does not require granting it project-wide Cloud Owner or Editor roles.
3. Create a JSON key for that service account. Store it outside source repositories,
   restrict file access to the OS account running the MCP, and retain it securely.
   If your organization prohibits service-account keys, this release's authentication
   method is not suitable; do not bypass that policy.
4. Copy the service account's `client_email`. In Search Console, a property owner
   adds it under **Settings → Users and permissions**. Full user access supports
   the intended read and sitemap operations; choose permissions deliberately.
5. Repeat the GSC user grant for each property you intend to access. Record each
   exact property identifier for the process allowlist.

Cloud IAM roles and GSC property permissions are different controls. Adding an email
to one does not automatically grant access in the other. See Google's
[service-account authentication](https://developers.google.com/identity/protocols/oauth2/service-account)
and [GSC user permissions](https://support.google.com/webmasters/answer/7687615?hl=en).

To check the key's structure locally without printing its private key, replace the
path and run from the checkout root:

```bash
uv run --locked --no-dev python - <<'PY'
import json
from pathlib import Path

path = Path("/absolute/private/path/google-key.json")
assert path.is_absolute(), "Use an absolute path"
with path.open() as source:
    credentials = json.load(source)
assert credentials.get("type") == "service_account", "Expected a service-account key"
assert credentials.get("token_uri") == "https://oauth2.googleapis.com/token"
assert credentials.get("private_key"), "Missing private key"
assert credentials.get("client_email"), "Missing service-account email"
print("Service-account structure: OK")
print("Service-account email:", credentials["client_email"])
PY
```

This does not validate key revocation or GSC permissions. Never paste the JSON key
into an agent conversation, issue, pull request, or documentation. Desktop OAuth
client files and saved user OAuth tokens are not supported by this server.

## 5. Configure your MCP client

Back up any existing client configuration securely before editing it; leave
unrelated settings intact. Put credentials in the process environment using only
their file path, not the key's contents. `.env` files are not loaded automatically.

### Clients with an mcpServers JSON configuration

Add this entry to the client's configuration, replacing both absolute paths and
the property. Merge it into an existing `mcpServers` object rather than replacing
other connections:

```json
{
  "mcpServers": {
    "google-search-console": {
      "command": "uv",
      "args": [
        "run", "--directory", "/absolute/path/to/mcp-google-search-console",
        "--locked", "--no-dev", "mcp-google-search-console"
      ],
      "env": {
        "GOOGLE_APPLICATION_CREDENTIALS": "/absolute/private/path/google-key.json",
        "GSC_ALLOWED_SITES": "[\"sc-domain:example.com\"]",
        "GSC_ENABLE_SITEMAP_WRITES": "false"
      }
    }
  }
}
```

Use an absolute path to `uv` if a desktop host cannot find it on PATH. If your host
supports tool timeouts, allow enough time for authentication and bounded read retries
(240 seconds accommodates the default budgets). Configuration file locations and
timeout setting names vary by client; use your client's own stdio setup instructions.

### Codex TOML configuration

Add the following to your user-level Codex `config.toml`, or to a trusted project's
`.codex/config.toml`. These table names must appear only once in that file:

```toml
[mcp_servers.google-search-console]
command = "uv"
args = ["run", "--directory", "/absolute/path/to/mcp-google-search-console", "--locked", "--no-dev", "mcp-google-search-console"]
enabled = true
required = true
startup_timeout_sec = 30
tool_timeout_sec = 240
enabled_tools = [
  "list_sites", "get_site", "query_search_analytics",
  "inspect_url", "list_sitemaps", "get_sitemap",
]

[mcp_servers.google-search-console.env]
GOOGLE_APPLICATION_CREDENTIALS = "/absolute/private/path/google-key.json"
GSC_ALLOWED_SITES = '["sc-domain:example.com"]'
GSC_ENABLE_SITEMAP_WRITES = "false"
```

`required = true` makes a connection startup failure explicit. Project-local config
is loaded only for trusted projects. See the
[official Codex MCP documentation](https://developers.openai.com/codex/mcp) for
configuration locations, tool restrictions, timeouts, and connection management.

If you install with `python -m pip install .` in a separate virtual environment,
use that environment's `mcp-google-search-console` executable as `command` and omit
the `uv` arguments. On Windows its executable is under the environment's `Scripts`
directory rather than `bin`.

## 6. Validate and connect

Validate JSON/TOML in your editor before restarting the host. For Codex, you can also
run this from the checkout root after substituting the actual configuration path:

```bash
uv run --locked --no-dev python - <<'PY'
import tomllib
from pathlib import Path
from mcp_google_search_console.config import Settings

config_path = Path("/absolute/path/to/config.toml")
with config_path.open("rb") as source:
    config = tomllib.load(source)
server = config["mcp_servers"]["google-search-console"]
settings = Settings.from_env(server["env"])
assert settings.credentials_file and settings.credentials_file.is_absolute()
assert settings.allowed_sites, "Choose at least one explicit property"
assert not settings.enable_sitemap_writes, "Start read-only"
print("TOML and GSC settings: OK")
PY
```

This reads configuration only, not the credential file or Google. From your intended
Codex project directory, inspect the resolved entry with:

```bash
codex mcp get google-search-console
```

Expected: your configured command, arguments, and allowlist. Do not share its output
without checking it for private paths or identifiers. This command is not a connection test.

Restart the MCP host or its connection, then inspect its tool catalog. In a fresh
Codex session, `/mcp` shows active connections. Expect `google-search-console` with
six read tools from the [tool list](reference.md#tools), no sitemap write tools.

Do not run an MCP OAuth login for this server. Service-account authentication is
performed lazily when a tool first contacts Google; startup/tool discovery need no key.

## 7. Test live reads and restrictions

These calls contact Google and return account data. Use only your authorized
properties; keep responses private. Run one test at a time and stop on errors.
Use a tool inspector or ask your agent to call the named tool with the JSON arguments.

### Property access

Call `list_sites` with `{}`. The result should include your accessible, allowed
property; an empty list may mean the account has no matching property grant.
Then call `get_site`:

<!-- tool: get_site -->
```json
{"site_url": "sc-domain:example.com"}
```

Expected: the property's `siteUrl` and `permissionLevel`. Other accessible properties
are intentionally hidden when they are not in `GSC_ALLOWED_SITES`.

### Search Analytics

Call `query_search_analytics`. Replace dates with a past period available in your
property; the illustrative dates below do not update themselves:

<!-- tool: query_search_analytics -->
```json
{
  "site_url": "sc-domain:example.com",
  "query": {
    "startDate": "2026-08-01",
    "endDate": "2026-08-07",
    "dimensions": ["page"],
    "type": "web",
    "dataState": "final",
    "rowLimit": 10,
    "startRow": 0
  }
}
```

Expected: a successful raw response, possibly with rows containing `clicks`,
`impressions`, `ctr`, and `position`. A successful empty result is valid and is not
proof of indexing failure. Dates are inclusive Pacific dates; query parameters and
provider limits are explained in the [reference](reference.md#search-analytics-query).

### URL inspection

Call `inspect_url` for a known page within the property:

<!-- tool: inspect_url -->
```json
{
  "site_url": "sc-domain:example.com",
  "inspection_url": "https://example.com/",
  "language_code": "en-US"
}
```

Expected: an `inspectionResult` object with Google's available stored information.
A reported indexing problem can mean the tool worked correctly. Missing fields
remain missing. This is not a live test or a request to index the page.

### Sitemaps

Call `list_sitemaps`:

<!-- tool: list_sitemaps -->
```json
{"site_url": "sc-domain:example.com"}
```

If `sitemap` entries are returned, copy an entry's exact `path` into `feedpath`
when calling `get_sitemap` (substitute the actual returned path):

<!-- tool: get_sitemap -->
```json
{
  "site_url": "sc-domain:example.com",
  "feedpath": "https://example.com/sitemap.xml"
}
```

Expected: submitted sitemap metadata, including processing warnings/errors when
present. No sitemap entries is a valid state; in that case the `get_sitemap` test
remains unverified. Neither call fetches the hosted XML or enumerates its page URLs.

### Property restriction

With only `sc-domain:example.com` allowed, call `get_site` for a different identifier:

<!-- tool: get_site -->
```json
{"site_url": "sc-domain:example.org"}
```

Expected: MCP `isError: true` with `error.code` equal to `property_not_allowed`.
The server rejects this before sending that property request to Google. Do not
broaden the allowlist or use another connector to bypass the test.

Also confirm `submit_sitemap` and `delete_sitemap` remain absent from tool discovery.
There is no need for a live mutation to verify the default read-only configuration.

## 8. Optional sitemap writes

Finish read tests first. Enabling writes changes the OAuth scope to `webmasters`
and exposes both sitemap operations for every allowed property. Google permissions
still apply. This flag is not per-call human approval.

1. Change `GSC_ENABLE_SITEMAP_WRITES` to the string `"true"` in the server's environment.
2. If the client has a tool allowlist, add `submit_sitemap` and `delete_sitemap`.
   The Codex sample's six-tool `enabled_tools` list must become an eight-tool list.
3. Configure your host's write approvals. In Codex, set
   `default_tools_approval_mode = "prompt"` under `[mcp_servers.google-search-console]`,
   not under its `.env` table. See the
   [configuration reference](https://developers.openai.com/codex/config-reference).
4. Restart and confirm all eight tools are available. Discovery performs no mutation.

If a live write test is needed, use a dedicated valid sitemap whose exact property
and URL you are authorized to manage. Explicitly approve submission of that URL,
then inspect its state with `get_sitemap`. Delete only that dedicated test submission
if separately authorized. Never delete a production submission just to test the tool.

Google's empty write success becomes `{}`. Submission acceptance is not successful
processing or indexing. Deleting a submission does not delete its hosted file or
deindex its pages. If `outcome_unknown` is true, check the current submission state
before considering another mutation; writes are not automatically retried.

To return to read-only, set the flag back to `"false"`, remove the two write tools
from any client allowlist, and restart the connection.

## 9. Troubleshooting and disabling the connection

| Symptom | What to check |
| --- | --- |
| `uv` or executable not found | Install dependencies and use the absolute executable path visible to your host |
| Startup timeout | Complete installation first; inspect stderr and the host startup timeout |
| MCP absent from Codex | Config location, project trust, and a fresh session; inspect the resolved entry |
| `configuration_error` | JSON allowlist syntax, supported environment values, and the correct `.env` table |
| `credentials_missing` | `GOOGLE_APPLICATION_CREDENTIALS` in the MCP process environment |
| `credentials_invalid` | Absolute path, file access, service-account type, token URI, and key format |
| `authentication_failed` | Key validity, system clock, and network/TLS access to Google's token endpoint |
| `permission_denied` | Search Console API enablement and the service account's GSC property permissions |
| `property_not_allowed` | Exact property spelling in `GSC_ALLOWED_SITES`, including URL-prefix details |
| `invalid_request` | Dates and compatible query dimensions, filters, aggregation, and search type |
| `quota_exceeded` | Stop repeated tests and check the applicable Google quota |
| `transport_error` | Network access and timeouts; environment-configured proxies are not supported |
| `response_too_large` | Reduce requested rows, or deliberately adjust the configured response limit |
| Writes absent after opt-in | Restart, confirm the process flag, and update the host tool allowlist |

See [error semantics](reference.md#result-and-error-contract) before interpreting an
error as missing data. Never publish credential files or unredacted diagnostic output.

To disable this connection, use your host's disable control or remove only its
configuration entry. In Codex, `enabled = false` under the server table disables
it. Restart afterward. If restoring a backup, preserve unrelated settings changed
since it was made. Disabling the MCP does not revoke its Google key or property access.

Your setup is ready for use when installation and discovery succeed, authorized
reads return valid responses, and the allowlist rejection behaves as expected.
Record skipped tests (for example, no submitted sitemap) separately from passes.
