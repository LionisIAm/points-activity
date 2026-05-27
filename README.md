# points-activity

Extract loyalty points and miles account activity from airline and hotel loyalty programs into a unified CSV — using your own logged-in browser session. No credentials are ever stored, nothing leaves your machine.

## What it does

For each supported loyalty program, the skill:

1. Opens the program's activity page in your connected Chrome
2. Waits for **you** to confirm you're logged in (it does NOT log in for you)
3. Extracts your transaction history via the program's internal JSON API, or by reading the rendered page when no API is available
4. Outputs a unified CSV: `Date, Description, Amount` (newest-first, signed amounts — earn `+`, redeem `−`)
5. Reports your current balance and the actual date range covered

## Supported programs

| Program | Method | History depth |
|---|---|---|
| World of Hyatt | Internal JSON API (0-based paging) | Full |
| United MileagePlus | Internal JSON API (with runtime token capture) | Full |
| IHG One Rewards | DOM scrape | ~365 days (program limit) |
| Accor ALL | DOM scrape (year accordions) | Full |
| Air Canada Aeroplan | DOM scrape (2-year filter) | 2 years (program limit) |
| Alaska Atmos Rewards | DOM scrape (Shadow DOM traversal) | 24 months (program limit) |
| Bilt Rewards | Internal JSON API (month+year iteration) | Full |

Plus a **generic playbook** for programs without a dedicated sub-skill (Marriott, Hilton, Delta, Amex MR, etc.) — Claude tries API-first, falls back to DOM, then to export-to-excel if available.

## Requirements

- [Claude Code](https://claude.com/claude-code)
- [Claude in Chrome](https://www.anthropic.com/claude-code) extension connected to a Chrome window
- A loyalty program account, logged in, in that Chrome window

## Install

### Claude Code CLI

```
/plugin marketplace add LionisIAm/points-activity
/plugin install points-activity@points-activity
```

Use the `owner/repo` shorthand (or a full `https://github.com/LionisIAm/points-activity.git` URL). A bare `github.com/owner/repo` without the scheme is misparsed and fails to clone.

(`points-activity@points-activity` = plugin name `@` marketplace name — both happen to be the same in this single-plugin repo.)

After install, restart your Claude Code session or run `/plugin reload-plugins`.

### Claude Desktop (Cowork)

Cowork does **not** register third-party marketplaces through its own "Add marketplace" dialog yet — that path is blocked upstream ([anthropics/claude-code#41653](https://github.com/anthropics/claude-code/issues/41653), "External plugin sources are not yet supported"). The working path uses Claude Code CLI, which Cowork mirrors:

1. Install via Claude Code CLI (see above) — this registers the marketplace under `~/.claude/plugins/`.
2. In Claude Desktop, open the plugin **Directory → Plugins → "Code"** tab. `points-activity` shows up there (the "Code" tab mirrors your Claude Code CLI marketplaces) and you can enable/install it from that view.

This requires Claude Code CLI installed on the same machine — Cowork shares its `~/.claude/plugins/` state.

> **Note:** The `points-activity.plugin` zip attached to each [release](https://github.com/LionisIAm/points-activity/releases) is an artifact for future use (e.g. air-gapped or org-managed installs). It is **not** a Chrome browser extension and cannot be installed via Chrome's "Install Unpacked Extension" — Cowork plugins are a separate concept.

### Manual (any runtime that reads `~/.claude/skills/`)

```bash
git clone https://github.com/LionisIAm/points-activity.git
cp -R points-activity/skills/* ~/.claude/skills/
```

Restart your Claude session. Useful for development, custom hosts, or runtimes without a plugin marketplace.

## Usage

Just ask Claude in natural language. Examples:

> "get my Hyatt points activity for the last 6 months"
> "pull my United mileage activity since Jan 2024 and tell me my balance"
> "export everything from https://all.accor.com/account/en/global-transaction-history"
> "update my IHG sheet"

The orchestrator skill (`points-activity`) figures out which program is meant, delegates to the program-specific sub-skill if one exists, otherwise uses the generic playbook.

## Output contract

Every program emits the same shape so downstream tools can be uniform:

- **CSV columns**: `Date`, `Description`, `Amount` (signed integer — earn `+`, redeem `−`)
- **Filename**: `<program>_activity_<from>_<to>.csv`, where `<from>` and `<to>` are the **actual** covered range (oldest..newest row), not the requested range — so the name never overstates coverage
- **Balance**: reported alongside the file
- **Collapsing**:
  - Redemptions / flights / reward bookings keep their **real** transaction date (each its own row, so you can match against itineraries)
  - Earnings / transfers / bonuses are moved to the **last day of their month** and identical `(date, description)` rows are summed
  - Zero-amount rows dropped
- **Spendable currency only**: for programs with multiple currencies (Accor reward vs status, United miles vs PQP), only the spendable one is included

## What you can do with the CSV

That part is up to you. Common uses:
- Drop into a spreadsheet for personal record-keeping
- Reconcile against booking confirmations and invoices
- Feed into a finance / budgeting tool that accepts CSV imports
- Diff month-over-month to spot unexpected redemptions

This plugin's scope ends at CSV. Integrations with specific finance tools are out of scope here.

## Adding a new program

See [CONTRIBUTING.md](CONTRIBUTING.md). The short version: clone an existing sub-skill, find the program's internal endpoint with DevTools, write a small extraction script and transform, add it to the routing table, open a PR.

## Security

- Runs in your own Chrome with your own session
- No credentials are stored, transmitted, or asked for
- No telemetry, no analytics, no remote logging
- CSV is written locally; nothing is sent over the network

See [SECURITY.md](SECURITY.md) for vulnerability reporting and the supply-chain trust model.

## Disclaimer

This tool extracts data from **your own** loyalty accounts using each program's internal APIs and page contents. Use of internal/private APIs may violate some programs' Terms of Service. This is a personal record-keeping tool — use at your own discretion. Maintainers are not liable for any consequences arising from use.

## License

[MIT](LICENSE)
