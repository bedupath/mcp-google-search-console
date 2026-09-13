---
name: gsc-verify
description: Run scoped offline lint, typing, tests, MCP protocol checks, and package builds for this GSC MCP repository. Use to verify changes without connecting to live Google properties.
---

# Offline verification

Read root `AGENTS.md` and choose the narrow tests matching the changed boundary:

- Inputs/configuration: `tests/test_models_config.py`.
- API requests, raw responses, scope enforcement, and retry behavior: `tests/test_client.py`.
- Service-account signing/refresh without Google calls: `tests/test_auth.py`.
- Tool catalog, schemas, error flags, and stdio entrypoint: `tests/test_server.py`.
- Contributor skills and package boundaries: `tests/test_repository.py`.

For a completed implementation run the root verification commands, including the
full test suite and wheel/sdist build. Never set real Google credentials to make
tests pass. The stdio smoke test intentionally runs without credentials; mocked
HTTP tests must remain network-isolated.

Inspect failures before changing anything. Verification does not authorize a
behavior change, a live call, staging, a commit, or package publication. If testing
packaging, install only into a disposable local environment, not the user's global
Python environment.

Report exact commands/results and distinguish local protocol/authentication mocks
from live Google authorization and end-user host acceptance. A successful submit
mock cannot establish sitemap processing or page indexing.
