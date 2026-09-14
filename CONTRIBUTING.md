# Contributing

Contributions are welcome: bug fixes, documentation improvements, tests, and focused
API support. Small fixes can go straight to a pull request. Discuss new tools,
authentication modes, dependencies, or breaking public contracts in an issue before
investing in an implementation. Report vulnerabilities using [SECURITY.md](SECURITY.md),
not a normal issue or pull request.

## Project scope

This is a minimal, non-opinionated Google Search Console client and MCP server.
The eight tools in [README.md](README.md#tools) expose provider operations; consumers
own SEO strategy, date windows, pagination, interpretation, storage, and approvals.
Do not add scores, recommendations, workflow prompts, crawling, scheduling, or other
providers as incidental improvements.

Preserve raw Google response fields, including absent/unknown inspection states and
incomplete-data metadata. Submitted sitemap counts are not indexed counts. Failed
requests are errors, not empty successful data. Keep explicit property selection,
read-only defaults, and client-side guards for sitemap writes.

## Local setup

Use Python 3.11 or newer and [uv](https://docs.astral.sh/uv/). From the repository root:

```bash
uv sync --locked
```

No Google account, service-account key, `.env`, or live property is needed to develop
and run tests. Tests use synthetic credentials and mocked HTTP. Never make a live
sitemap mutation to demonstrate that a contribution works.

Runtime setup is documented separately in [Setup and testing](docs/setup-and-testing.md).
Source is under `src/mcp_google_search_console/`; offline tests are under `tests/`.
Agent-assisted contributors should also read [AGENTS.md](AGENTS.md).

## Branches and pull requests

`main` is the only permanent integration branch and should remain buildable and
tested. There is no permanent `dev` or release branch. Published version tags, not
the moving `main` branch, identify releases.

1. External contributors fork the repository and clone their fork. Collaborators
   with write access can use a branch in the upstream repository. Access to a
   private repository and permission to fork it depend on its organization settings.
2. Start a short-lived branch from an up-to-date `main`, for example
   `fix/token-refresh`, `feat/oauth-support`, or `docs/setup`.
3. Make one focused change, including relevant tests and documentation. Avoid
   unrelated formatting, dependency upgrades, or generated files.
4. Push the branch to your fork (or upstream if authorized) and open a PR targeting
   `bedupath/mcp-google-search-console:main`. Draft PRs are welcome for unfinished work.
5. Run the checks below, address review feedback, and resolve review conversations.
   If the base branch changes, update the branch and rerun affected checks.
6. A maintainer reviews external contributions and squash-merges accepted PRs after
   required checks pass. Delete the source branch after merging.

Use a Conventional Commit PR title, such as `fix: handle expired access tokens`,
`docs: clarify property configuration`, or `feat!: change the query schema` for a
breaking change. Individual work-in-progress commits need not follow this format;
the PR title becomes the squash commit title. Explain compatibility changes in the PR.

PRs should state the problem, the change, verification performed, and any effect on
tool schemas, Python APIs, environment variables, permissions, or Google requests.
The [PR template](.github/pull_request_template.md) provides a short checklist.
Documentation-only changes should say so; a live integration test is not expected.

## Verification

Run targeted tests while developing. Before requesting merge, run from the repository root:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest --cov=mcp_google_search_console --cov-report=term-missing
uv build
git diff --check
```

To fix formatting, run `uv run ruff format .`. For dependency changes, update
`pyproject.toml` and regenerate `uv.lock` with `uv lock`, then run `uv sync --locked`
and the verification commands. Do not hand-edit the lockfile.

CI runs lint, formatting, typing, tests, and packaging on Python 3.11–3.14. Tests
must remain offline and usable by fork PRs without repository secrets. Mocked
authentication and stdio tests are not proof of live Google authorization or indexing.

## Privacy and security

Use reserved example domains and synthetic responses. Do not include credentials,
tokens, private URLs, customer/project identifiers, analytics exports, or local
machine paths in source, fixtures, PRs, issues, or logs. Generated environments,
coverage files, and build artifacts should remain untracked.

The ignore rules are not a secret scanner. If a real key is exposed, revoke or
rotate it; deleting the text or making a repository private is not remediation.
Do not use privileged CI or production credentials to run untrusted contribution code.

## Maintainer repository setup

The workflow above is project policy. Files in this repository do not configure
GitHub's branch protection or merge settings. Apply and verify these settings
separately before relying on automated enforcement:

- Protect `main`: require pull requests, passing CI, and resolved review
  conversations; disallow force pushes and branch deletion.
- After CI has run on GitHub, select all four actual `verify` matrix checks as
  required checks (Python 3.11, 3.12, 3.13, 3.14). Do not guess check identifiers.
- While there is one maintainer, require zero approving reviews so their own PRs
  can merge after CI. External contributions still receive maintainer review.
  Require one approval once another active maintainer can review changes.
- Allow squash merging only, use the PR title for the squash commit title, and
  enable automatic deletion of merged source branches. Keep a linear `main` history.
- Verify the private reporting channel in [SECURITY.md](SECURITY.md) before making
  the repository public. Do not publish an unmonitored or unverified contact.

Protection availability depends on repository visibility and the organization's
GitHub plan. See [branch protection](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
and [squash merge settings](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/configuring-commit-squashing-for-pull-requests).

## Releases

Releases are maintainer-controlled, not automatically published on merge.

1. Prepare a release PR from `main`. Keep the version in `pyproject.toml` and
   `src/mcp_google_search_console/__init__.py` consistent, regenerate `uv.lock`,
   and document notable changes and any breaking changes in the release notes.
2. Merge after verification and passing CI. Build and inspect the wheel and source
   archive from the exact release commit.
3. Tag that tested `main` commit using `vMAJOR.MINOR.PATCH`, for example `v0.1.0`,
   and create a GitHub release. Never move an already published version tag.
4. Publish to a package registry only when separately authorized and configured.
   This workflow does not assume that a PyPI project or publishing credentials exist.

During `0.x`, use patch releases for compatible fixes and minor releases for
features or breaking changes; explicitly describe every breaking change. After
`1.0`, breaking changes require a major version increment. There are no maintained
backport branches or promises of support for older release lines at this stage.
