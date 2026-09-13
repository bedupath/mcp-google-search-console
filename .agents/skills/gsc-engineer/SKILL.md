---
name: gsc-engineer
description: Implement or fix this repository's Google Search Console client, authentication, input schemas, and MCP tools. Use for code changes, not SEO strategy or live account operations.
---

# GSC engineering

Read root `AGENTS.md`, the relevant module, and its tests first. Keep transport in
`server.py`, provider behavior in `client.py`, and reusable input validation in
`models.py`. A Python consumer must not need the MCP server to call Google.

When touching a Google contract, verify the relevant primary reference linked in
README.md. Do not infer API fields or capabilities from GSC UI labels. Supply exact
property identifiers and encode property/sitemap path segments once; never turn
a caller-supplied URL into a direct outbound fetch.

Preserve the provider JSON object, including absent/unknown fields and nested
rich-result issues. Search Analytics returns limited top rows, not an exhaustive
URL inventory. Add a regression at the HTTP request boundary for parameter changes,
and at the MCP session boundary for schema/result changes.

Permission changes need tests for both catalog exposure and direct library calls.
Allowlist/write checks happen before authentication. Keep token handling lazy,
credential-safe, and independent of tool discovery. Do not retry ambiguous writes
or turn failed reads into empty successful responses.

Use synthetic data and mocked Google endpoints during implementation. Run targeted
tests while editing, then the root verification commands. Update public examples
when behavior changes; leave strategy and workflows to consumer-owned skills.
