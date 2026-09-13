# Contributor Agent Guide

This is the standalone Bedupath Google Search Console MCP repository. Sibling
projects are consumers, not part of this repository's scope.

## Product contract

- Keep the MCP non-opinionated: Google operations and data, not SEO strategies,
  scores, recommended actions, reporting periods, or workflow prompts.
- The public tool surface is the eight operations documented in README.md.
  Do not add account management, crawling, scheduling, or new providers without
  an explicit scope change.
- Responses remain raw provider objects. Never relabel sitemap `submitted` as
  indexed, collapse unknown inspection states to not indexed, or treat API
  errors as successful empty data.
- One service-account identity may access multiple properties. Every scoped
  operation uses an exact `site_url`; no global active-site state.

## Code map

- `src/mcp_google_search_console/models.py`: validated native API inputs.
- `config.py`, `auth.py`: process permissions and lazy Google authentication.
- `client.py`: reusable async provider operations, without an MCP dependency.
- `server.py`: stdio transport, schemas, annotations, and MCP error mapping.
- `tests/`: synthetic provider, authentication, and protocol tests.

## Safety and change boundaries

- Read relevant source/tests before changing a contract. Preserve unrelated edits.
- Do not stage, commit, push, publish, or release without explicit user permission.
  Commit permission never implies push permission.
- Do not read real credential files or call live Google services for ordinary
  implementation/tests. Live checks require an explicit target and authorization;
  submit/delete require explicit authorization for that exact mutation.
- Never put real credentials, customer property names, private analytics, or host
  configuration in this reusable repository. Use reserved example domains in tests.
- Maintain read-only default scope, hidden disabled write tools, client-side write
  guards, allowlist enforcement, fixed Google origins, and sanitized errors.
- Run only offline checks by default. A stdio test subprocess is permitted; a
  hosted service, deployment, or live integration setup is not implied.

## Local skills

Use the relevant entrypoint before its workflow:

- [gsc-engineer](.agents/skills/gsc-engineer/SKILL.md): implementation of provider,
  authentication, validation, or MCP contracts.
- [gsc-reviewer](.agents/skills/gsc-reviewer/SKILL.md): read-only change and security review.
- [gsc-verify](.agents/skills/gsc-verify/SKILL.md): offline tests, typing, lint, and packaging.

These are development skills only. Do not register them as MCP prompts/resources
or include them in the runtime wheel.

When maintaining skills:

- Keep each `.agents/skills/<name>/SKILL.md` self-contained, with `name` and
  `description` YAML frontmatter. Distinguish implementation, read-only review,
  and offline verification, preserving user authorization boundaries.
- Include only repository-specific guidance that changes a maintainer's decisions;
  do not duplicate this guide or add consumer-specific SEO strategy.
- Check links and frontmatter, then run `uv run pytest tests/test_repository.py`.

## Verification and handoff

```bash
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov=mcp_google_search_console --cov-report=term-missing
uv build
git diff --check
```

Update README examples when signatures/configuration change. Report what was
implemented, checks actually run, and any live-validation gap. Do not claim that
offline mocks establish GSC property access, successful sitemap processing, or indexing.
