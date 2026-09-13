---
name: gsc-reviewer
description: Review changes in this GSC MCP repository for API-contract errors, permission bypasses, data corruption, credential exposure, and missing tests. Review is read-only unless a fix is explicitly requested.
---

# GSC change review

Read root `AGENTS.md` and inspect the requested diff plus its callers/tests. Lead
with concrete correctness/security findings, including file/line evidence and the
request that would trigger the problem. Separate confirmed defects from live checks
that cannot be established offline.

Trace affected calls from tool schema through validation, property/write guards,
authentication, encoded Google request, and MCP result/error. Check direct Python
calls as well as advertised tools: annotation hints alone do not enforce permissions.

Pay particular attention to scope widening, allowlist empty-versus-unset behavior,
credential-derived token endpoints, redirects, token logging, and unbounded retries.
For writes, inspect ambiguous transport outcomes and accidental resubmission.

Check that unknown indexing states remain unknown, sitemap submitted counts are not
indexed counts, incomplete analytics metadata survives, and upstream failures cannot
be mistaken for “no problems.” Provider fields must not disappear in a new response model.

Use offline diagnostic tests when relevant. Do not load credentials, call a live
property, edit code, stage files, or apply fixes merely because a review found a defect.
