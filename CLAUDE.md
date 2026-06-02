# CLAUDE.md

Project context for AI assistants working in this repo. End users → read [README.md](README.md). Code contributors → read [CONTRIBUTING.md](CONTRIBUTING.md). Security reporting → [SECURITY.md](SECURITY.md).

## What this is

A Claude plugin (`points-activity`) that extracts loyalty points/miles activity from airline and hotel programs into a unified CSV. One **orchestrator** skill routes to **7 program-specific sub-skills** (Hyatt, United, IHG, Accor, Aeroplan, Alaska, Bilt) or falls back to a generic playbook for unsupported programs. Skills drive the user's **own logged-in browser** via the **Claude in Chrome** MCP — the plugin never asks for or stores credentials.

Solo-maintained, MIT, public. No commercial backing.

## Repo layout

```
.
├── .claude-plugin/marketplace.json   # plugin marketplace manifest (Code CLI + Cowork)
├── plugin.json                       # plugin manifest (name, version, description, author)
├── skills/
│   ├── points-activity/              # ORCHESTRATOR — entry point + routing + general playbook
│   │   ├── SKILL.md
│   │   ├── evals/trigger_eval.json   # positive + near-miss trigger cases
│   │   └── scripts/activity_output.py  # SHARED output contract (write_activity)
│   └── <program>-activity/           # one per supported program (hyatt, united, ihg, ...)
│       ├── SKILL.md
│       ├── scripts/
│       │   ├── fetch_activity.js     # API path (hits internal endpoint)
│       │   ├── scrape_activity.js    # DOM path (reads rendered page) — alternative to API
│       │   ├── dump_console.js       # console-dumps rows for read_console_messages
│       │   ├── capture_auth.js       # ONLY where runtime-attached auth needs XHR hooking (e.g. United)
│       │   ├── transform.py          # parses console dump → unified CSV via activity_output.py
│       │   └── activity_output.py    # COPY of the shared helper (duplicated per skill — see below)
│       └── tests/
│           ├── fixtures/raw_dump.txt # sanitized sample console dump
│           └── test_transform.py     # stdlib unittest, no pytest dep
├── .github/
│   ├── workflows/release.yml         # on `v*` tag → builds .plugin, attaches to GitHub Release
│   ├── ISSUE_TEMPLATE/               # bug / new-program / playbook-broken
│   └── PULL_REQUEST_TEMPLATE.md
├── README.md / CONTRIBUTING.md / SECURITY.md / LICENSE / CLAUDE.md (this)
└── .gitignore                         # csv excluded so no real account data ever commits
```

> **Test coverage is being backfilled.** Not every `<program>-activity/` has a
> `tests/` dir yet (currently: alaska, bilt). The rest land during the v0.3
> contract migration. CI (`.github/workflows/ci.yml`) runs whatever
> `test_transform.py` files exist plus the repo-wide registration checks
> (`tests/test_registration.py`), so coverage only ratchets up.

## Critical conventions

### Unified output contract
Every program emits identical CSV shape via `activity_output.py:write_activity(program, rows, out_dir, requested_from, requested_to, balance)`:

- **Columns**: `Date, Description, Amount` — no `Program` column (program is in filename), no `Unit` column (points and miles never mix in one file)
- **Filename**: `<program>_activity_<from>_<to>.csv` where `<from>/<to>` are the **actual covered range**, NOT the requested range (so the filename never overstates coverage)
- **Machine-readable stdout** the orchestrator parses literally:
  ```
  BALANCE: <int or "unknown">
  COVERED: <from>..<to>
  REQUESTED: <from>..<to>  (or "all" if unbounded)
  FILE: <absolute path>
  ROWS: <n>
  ```

**Do not diverge from this contract.** Reordering or renaming the stdout lines breaks downstream consumers.

### Collapsing rules (shared across programs)
- Redemptions / flights / reward bookings → keep **real** transaction date, each its own row (so they can be matched against itineraries/invoices)
- Earnings / transfers / bonuses → move date to **last day of the month**, then collapse identical `(date, description)` rows by summing
- Drop zero-amount rows after collapsing
- Keep only spendable currency (e.g. United miles, not PQP; Accor reward points, not status points)

### `activity_output.py` is intentionally duplicated per sub-skill
Each sub-skill has its own copy (~72 lines). This is packaging redundancy by design — skills ship as self-contained units that work even if loaded in isolation. **If you change one copy, change all of them**, or the contract drifts silently per program.

### Code style
- **Python**: stdlib only — no external deps, no `pip install`. Scripts must be runnable as `python3 transform.py <raw_dump.txt> <out_dir>`.
- **JS**: small, self-contained, no bundlers. Modern syntax fine.
- **Comments**: preserve hard-won knowledge ("Pagination is 0-based — starting at 1 silently drops the newest page"), not narrate the obvious.

## Required MCP

Skills call browser-control tools by short names: `navigate`, `javascript_tool`, `read_console_messages`, `tabs_context_mcp`, `present_files`. The **Claude in Chrome** MCP must be connected by the host runtime. Hosts may expose them with prefixes (e.g. `mcp__Claude_in_Chrome__navigate`) — Claude resolves them automatically.

Without Claude in Chrome MCP, all sub-skills should **refuse cleanly** rather than fake a result.

## Common tasks

### Run all unit tests
```bash
for d in skills/*/tests; do
  [ -f "$d/test_transform.py" ] && (cd "$d" && python3 test_transform.py)
done
```

### Build .plugin locally (matches CI logic)
```bash
mkdir -p /tmp/build/points-activity
rsync -a --exclude='.git' --exclude='.github' --exclude='dist' ./ /tmp/build/points-activity/
(cd /tmp/build && zip -r /tmp/points-activity.plugin points-activity/)
```

### Cut a new release
```bash
git tag -a vMAJOR.MINOR.PATCH -m "Release notes here"
git push origin vMAJOR.MINOR.PATCH
```
CI (`.github/workflows/release.yml`) builds `.plugin`, creates the GitHub Release, attaches the asset. Code CLI users with auto-update enabled get it on next start; others run `/plugin marketplace update points-activity`.

**Semver discipline:**
- **PATCH** (`v0.1.1`) — playbook fix after a program's API/UI changed; no contract change
- **MINOR** (`v0.2.0`) — new sub-skill, new orchestrator capability, README content additions
- **MAJOR** — backward-incompatible change to the unified output contract or skill triggering

## When adding or changing a program — update ALL of these

The single most common source of "I added X but the orchestrator doesn't see it" bugs:

| # | File | Why |
|---|---|---|
| 1 | `skills/<program>-activity/SKILL.md` | the sub-skill itself + triggering description |
| 2 | `skills/<program>-activity/scripts/` | fetch/scrape/dump/transform |
| 3 | `skills/<program>-activity/tests/` | fixture + `test_transform.py` (stdlib unittest) |
| 4 | `skills/points-activity/SKILL.md` | add row to routing table + period-handling note |
| 5 | `skills/points-activity/evals/trigger_eval.json` | positive + URL-only + at least 2 near-miss negative cases |
| 6 | `README.md` | "Supported programs" table; remove from "generic playbook" list if it was there |
| 7 | `CLAUDE.md` (this file) | "What this is" count + repo-layout note if structure changed |
| 8 | `plugin.json` | bump `version` if a release is intended |

If you change the **unified output contract**, change ALL `activity_output.py` copies in lockstep, including `skills/points-activity/scripts/activity_output.py`.

## Gotchas (hard-won knowledge — preserve in comments and respect)

- **Hyatt API pagination is 0-based**. `pageIndex=0` is the newest page; starting at 1 silently drops the newest ~15 transactions. Also `pageSize >= 200` returns `[]` — use 15.
- **United runtime auth header**. The SPA attaches `x-authorization-api: bearer <token>` at request time, not in localStorage. Use `capture_auth.js` to hook `XMLHttpRequest.prototype.setRequestHeader` and capture from a real request the page makes. Token expires per session.
- **Console-dump workaround**. Returning raw JSON from `javascript_tool` is sometimes blocked by the chat as "Cookie/query string data". Workaround: dump rows to `console.log` with a unique prefix (e.g. `HX###~...`), then `read_console_messages(pattern:"^HX\\d", ...)`.
- **Shadow DOM (Alaska)**. Recurse through `el.shadowRoot` to reach inner components.
- **Year accordions (Accor)**. Click to expand collapsed yearly sections before scraping.
- **Aeroplan Family Sharing**. Balance can pool across members — do NOT enforce sum-to-balance reconciliation there.
- **Session expiry**. Never blind-retry on zero rows or HTTP 401/403 — stop and ask the user to re-login. A month-old session almost always needs fresh login.
- **0-based vs 1-based off-by-one**. The single most likely silent bug when adding a new program. Verify by checking `newest` returned vs newest visible on the page.

## What Claude should NOT do here

- ❌ Log in to loyalty programs on the user's behalf (the user must do this themselves)
- ❌ Store, transmit, or log credentials
- ❌ Send any data outside the user's machine (no telemetry, no analytics, no remote logging)
- ❌ Add external dependencies (`pip install`, `npm install`) — stdlib + browser-only
- ❌ Bypass the unified output contract — every program writes via `write_activity`
- ❌ Add `Co-Authored-By:` trailers to commits (clean history convention)
- ❌ Promise that Cowork's "Add marketplace" UI works for third-party sources — Anthropic's `remoteMarketplaceClient` rejects them upstream ([anthropics/claude-code#41653](https://github.com/anthropics/claude-code/issues/41653))

## Cross-runtime install paths (what actually works)

| Runtime | Path | Notes |
|---|---|---|
| Claude Code CLI | `/plugin marketplace add github.com/LionisIAm/points-activity` + `/plugin install points-activity@points-activity` | Tested, primary path |
| Claude Desktop with Cowork (same machine) | Auto-discovered via shared `~/.claude/plugins/installed_plugins.json` once installed in CLI | Verified |
| Cowork "Add marketplace" UI (third-party URL) | **Broken upstream** — rejected by Anthropic backend | Don't recommend |
| Manual any-host | `git clone` + `cp -R skills/* ~/.claude/skills/` | Useful for dev/custom hosts |

`.plugin` artifact in GitHub Releases is built by CI but mostly dead weight right now — kept for air-gapped/org-managed scenarios.

## Output directory convention

Sub-skills write CSVs to:
1. `$OUTPUTS_DIR` if set (Cowork convention — files surface as clickable cards in chat)
2. otherwise a host-provided path (e.g. `/tmp` or an arg the user passed)
