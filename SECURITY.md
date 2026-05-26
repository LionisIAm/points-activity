# Security

## Reporting vulnerabilities

If you discover a security issue — especially anything that could lead to credential exposure, auth-token theft, data exfiltration, or supply-chain compromise — please report privately:

- **Preferred**: Open a private GitHub Security Advisory at https://github.com/LionisIAm/points-activity/security/advisories/new

Please do **not** open a public issue for security-sensitive reports.

We aim to respond within 72 hours and to ship a fix or mitigation within 7 days for confirmed high-severity issues.

## Threat model

This plugin's scripts execute inside your own Chrome browser, in tabs where you are logged in to your loyalty/airline/hotel program accounts. That session context gives the scripts the same access **you** have to your own account data.

**What the scripts do:**
- Read account activity by calling the program's internal JSON API or by reading the rendered DOM
- In some sub-skills, hook `XMLHttpRequest.prototype` to capture auth headers attached by the page's own SPA at request time
- Write CSV files to your local filesystem
- Print machine-readable lines to your Claude Code terminal

**What the scripts do NOT do:**
- Ask for, store, transmit, or log credentials
- Send any data anywhere — no telemetry, no analytics, no remote endpoints
- Log in on your behalf
- Read accounts other than the one you have logged in

## Supply-chain considerations

Because these scripts run in your authenticated browser sessions, a compromise of this repository would mean compromise of users' loyalty/airline/hotel data — and potentially adjacent data depending on what the auth context allows.

Mitigations on our side:
- Maintainers must have 2FA enabled on GitHub
- All changes land via PR review — no direct pushes to `main`
- Releases are tagged manually; the `version` in `plugin.json` is bumped intentionally for each release
- Any code that hooks browser internals (XHR, fetch, headers, token handling) gets line-by-line review before merge
- No external dependencies — Python stdlib only, no npm packages, no bundlers

Mitigations on your side (if you install):
- Verify the plugin source is the expected namespace (`github.com/LionisIAm/points-activity`)
- Review release notes when auto-update applies a new version
- Be especially cautious about updates that touch `capture_auth.js` or any new XHR/fetch hooks
- Pin to a known-good version in your settings if you want to opt out of silent updates

## What's intentionally out of scope

- **We do not warrant or support the use of these scripts against any specific loyalty program.** Internal API endpoints can change without notice; ToS may prohibit programmatic access. This is a personal record-keeping tool and you accept the risk of using it.
- **We do not store, retrieve, or process data outside your machine.** If a future version did, that would be a fundamental scope change requiring its own security review and announcement.

## Coordinated disclosure

If a vulnerability requires user action (e.g. uninstalling, downgrading, or rotating tokens), we will:
1. Publish a security advisory on GitHub
2. Bump version with a clear note in `CHANGELOG.md`
3. If severe enough to warrant pulling the affected release, mark it as yanked in the marketplace
