# Security policy

## Reporting a vulnerability

Do not disclose vulnerabilities, exploit details, tokens, or private property data
in normal issues, pull requests, or discussions.

**Reporting channel setup is pending.** The repository is currently private, and
no monitored organization security contact has been confirmed for this policy.
Until a private channel is confirmed, do not send sensitive reports to a guessed
email address or assume that a repository issue is a private security advisory.
Existing collaborators can ask a maintainer to establish a private reporting
channel without including vulnerability details.

Before public launch, a maintainer must enable GitHub private vulnerability
reporting and verify that the
[private report form](https://github.com/bedupath/mcp-google-search-console/security/advisories/new)
is accessible and its notifications are monitored, or publish a confirmed monitored
organization security contact here. The form is the intended public-project
channel, not a claim that reporting is already enabled.

GitHub documents [how to enable private vulnerability reporting](https://docs.github.com/en/code-security/how-tos/report-and-fix-vulnerabilities/configure-vulnerability-reporting/configure-for-a-repository)
for public repositories. Do not change repository visibility merely to activate it
without the owner's authorization.

Once a private channel is available, include the affected version or commit,
impact, prerequisites, and minimal reproduction steps using synthetic credentials
and example domains. Include only redacted logs. Never attach a real Google key,
access token, customer analytics export, or data from another person's property.

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
