# points-activity

Extract loyalty points and miles account activity from airline and hotel loyalty programs into a unified CSV — using your own logged-in browser session. No credentials are ever stored. Extraction is fully local: the CSV is written to your disk and nothing is sent anywhere. **Optional** importers can then push that CSV into your own finance app (Finerd today; Monarch and Copilot scaffolded) via that app's MCP — only if you choose to install one.

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

### Easiest: let Claude walk you through it

Paste this prompt into your Claude Code session (CLI or the Claude Code inside Claude Desktop) and it will guide you, check prerequisites, and confirm the first run:

```
Help me install the points-activity plugin: https://github.com/LionisIAm/points-activity
It extracts my own loyalty points/miles activity (Hyatt, United, IHG, Accor, Aeroplan,
Alaska, Bilt) from my logged-in browser into a CSV. MIT-licensed, stores no credentials.

Walk me through it:
1. Confirm I'm in Claude Code (the /plugin command only works there). If I'm in a plain
   Claude.ai chat, tell me what I need instead.
2. Give me the exact commands to run — you can't run slash commands yourself, so I'll type
   them:
     /plugin marketplace add LionisIAm/points-activity
     /plugin install points-activity@points-activity
     /plugin reload-plugins
3. Check whether the "Claude in Chrome" browser tools are available in this session. If
   they're missing, tell me to connect Claude in Chrome (a connector in Claude Desktop; an
   MCP server in the CLI) — the plugin needs them to read my account pages.
4. Remind me I must be logged in to the loyalty program (e.g. hyatt.com) in that Chrome
   window first. The plugin never logs in for me and never stores credentials.
5. Once it's installed, have me try: "get my Hyatt points activity for the last 6 months"
   and tell me what to expect on the first run.
```

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

1. In the Claude Code CLI terminal, run just the marketplace-add (the `owner/repo` shorthand):
   ```
   /plugin marketplace add LionisIAm/points-activity
   ```
2. Open Claude Desktop → plugin **Directory → Plugins → "Code"** tab. `points-activity` appears there and its skills become available **immediately** — no separate install step or "+" click needed (the "Code" tab mirrors your Claude Code CLI marketplaces).

This requires Claude Code CLI installed on the same machine — Cowork shares its `~/.claude/plugins/` state. Cowork's own "Add marketplace" dialog won't work until the upstream bug is fixed.

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
  - Earnings / transfers / bonuses keep their **real** transaction date; identical `(date, description)` rows are summed
  - Zero-amount rows dropped
- **Spendable currency only**: for programs with multiple currencies (Accor reward vs status, United miles vs PQP), only the spendable one is included

## What you can do with the CSV

That part is up to you. Common uses:
- Drop into a spreadsheet for personal record-keeping
- Reconcile against booking confirmations and invoices
- Feed into a finance / budgeting tool that accepts CSV imports
- Diff month-over-month to spot unexpected redemptions

The CSV is the core deliverable, and for many people that's the whole story. If you
want it pushed into a finance app, **optional importers** (`skills/<app>-import/`) do
that via the app's MCP — `finerd-import` today, `monarch-import` and `copilot-import`
scaffolded. Importers are opt-in and fully decoupled: adding a loyalty program never
requires touching any importer, and never-delete is a hard rule for all of them. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

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
