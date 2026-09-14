# Security policy

## Reporting a vulnerability

Do not disclose vulnerabilities, exploit details, tokens, or private property data
in normal issues, pull requests, or discussions.

GitHub private vulnerability reporting is enabled for this public repository.
Sign in to GitHub and use the
[private report form](https://github.com/bedupath/mcp-google-search-console/security/advisories/new),
or open **Security → Advisories → Report a vulnerability**. This sends the report
through GitHub's private advisory workflow, not a public issue.

If the form is unavailable, ask a maintainer to restore the reporting channel
without including sensitive details. Do not send reports to a guessed email address.

Include the affected version or commit,
impact, prerequisites, and minimal reproduction steps using synthetic credentials
and example domains. Include only redacted logs. Never attach a real Google key,
access token, customer analytics export, or data from another person's property.

## Maintainer notifications

Maintainers responsible for security reports must watch this repository with
**Custom → Security alerts** (or **All Activity**) selected and keep notifications
enabled. For email delivery, also enable email for **Watching** in personal
notification settings. See [GitHub's notification instructions](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository#configuring-notifications-for-private-vulnerability-reporting).

Enabling the repository feature does not verify an individual's notification
preferences or email delivery. Confirm those separately and check private advisories
regularly; do not publish a test vulnerability solely to exercise notifications.

## Scope and support

Relevant reports include credential disclosure, property-allowlist bypasses,
unintended writes, authentication flaws, and unsafe outbound requests in this
package. Report vulnerabilities in Google or another upstream service through
that provider's own security process.

Security fixes target the latest release and current `main`; older release lines
do not have a backport commitment. Before the first release, use the current
`main` commit as the version reference. This volunteer-maintained project does not
promise a response deadline, bounty, or service-level agreement.

Coordinate publication of exploitable details with maintainers after a fix is
available. Avoid testing against live properties or third-party accounts without
their explicit authorization.

## If credentials were exposed

Revoke or rotate the affected Google key or token immediately through the provider.
Removing a file or rewriting Git history does not invalidate a leaked credential.
Notify the affected account owner privately; do not copy the credential into a report.
