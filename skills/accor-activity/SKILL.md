---
name: accor-activity
description: Extract Accor ALL (Accor Live Limitless) reward-points activity into the unified points-activity CSV (Date, Description, Amount) plus the current balance. Use whenever the user wants to pull, export, check, sync, or monitor their Accor / ALL points history, transaction history, reward points, stays, or reward-night redemptions — including recurring/scheduled monthly checks. Triggers on "get my Accor points", "update my ALL sheet", "Accor transaction history". Part of the points-activity skill suite; scrapes the statement (expands year accordions). Requires the user to be logged in to all.accor.com in the connected Chrome browser.
---
> **Unified output contract.** This sub-skill is part of `points-activity`. Its `scripts/transform.py` writes `Date, Description, Amount` and the filename `accor_activity_<from>_<to>.csv` (covered range) via the shared `scripts/activity_output.py`, and prints `BALANCE:/COVERED:/REQUESTED:/FILE:/ROWS:` to stdout. The orchestrator passes the requested period and reads those lines. References to `collapsed.csv` / `Points` / `Miles` below are the older single-program wording; the actual columns are `Date, Description, Amount`.


# Accor ALL Points Statement Extraction

Scrapes the rendered Accor points statement (global transaction history), expands all
year accordions, keeps only REWARD points, collapses, and outputs a points table.

## Prerequisites

- **Claude in Chrome** extension connected (`list_connected_browsers` → `select_browser`).
- User **logged in** to all.accor.com. Don't log in on their behalf.
- Verify login programmatically: the page title is "Your points statement ..." and a
  member name / reward-points balance is shown; there are no sign-in buttons.

## Why DOM scraping (not the API)

Accor's data sits behind `api.accor.com` with a Bearer JWT
(`localStorage['identification-token_all.accor']`) plus `apiKey` + `x-caller`
headers. The auth can be reconstructed (and e.g. `/orders/v1/contacts/me/orders`
returns 200 — but only bookings, 2 of them, not the point lines). The actual
points-statement endpoint never shows up in network logs or fetch/XHR hooks — the
data is delivered at first render and cached in Angular state. The rendered table is
complete and its reward-points sum reconciles to the balance, so scraping wins.

## Procedure

### 1. Open the page
`tabs_context_mcp(createIfEmpty:true)` → `navigate` to
`https://all.accor.com/account/en/global-transaction-history`. Confirm login. Keep `tabId`.

### 2. Scrape (expands years automatically)
Run `scripts/scrape_activity.js`. History is grouped into year accordions; the
current year is expanded, older years are COLLAPSED and their rows aren't in the DOM
until the year header is clicked. The script clicks every collapsed year, then parses
each `<tr class="simple-grid__tr--tbody">` (5 cells: Description, Date MM/DD/YYYY,
Reward, Status, Nights), keeping year context. Returns `{count, years}`, stashes rows
on `window.__accor`.

### 3. Dump and read back
Run `scripts/dump_console.js` (logs `AC###~ ...`), then
`read_console_messages(pattern:"^AC\\d", limit:60, tabId:...)`. (Direct JSON returns
are often blocked by the chat — the console path avoids it.)

### 4. Transform
Strip the `AC###: ` prefix, write the `~~`-delimited lines to a file
(e.g. `/tmp/raw.txt`), then:
```
python3 scripts/transform.py /tmp/raw.txt <output_dir> [from] [to] [balance]
# from/to are ISO yyyy-mm-dd or '-' for unbounded; balance is the current balance or omit.
```
Writes `collapsed.csv`, prints row count + reward total.

### 5. Present and sanity-check
`present_files` on `collapsed.csv`. As a sanity check, the reward-points total may
equal the current reward-points balance (true for accounts whose full history is
visible). If it does, great; if not, don't force it — older history may have rolled
off.

## The collapsed table (the deliverable)

`collapsed.csv`: columns `Date, Description, Points` (Points = REWARD points only;
Status points and Nights are intentionally ignored). Logic (in `scripts/transform.py`):

1. **Classify**: *redemption* = description starts "Stay paid with points:"; everything
   else (stays, Platinum bonus, partner earns like Flying Blue / Europcar / BILT) is an
   *earning/transfer*.
2. **Redemptions**: keep the real transaction date; each stays its own row (matched to
   invoices later); hotel name kept in the description.
3. **Earnings/transfers**: move the date to the last day of its month so repeated
   monthly items collapse.
4. **Collapse** by (Date, Description), sum reward Points.
5. **Drop zero-point rows** after collapsing (rows that only carried Status/Nights, or
   that net to zero, fall out).

## Recurring / scheduled use (monthly)

Run as a **scheduled task on the user's own machine** — needs the user's real
Chrome + live Accor session. Use the host's scheduling primitive: Cowork —
`mcp__scheduled-tasks__create_scheduled_task`; Claude Code — cron + headless
invocation. Caveats: local tasks run only while the computer is on and the app is
open; no completion/failure notifications yet; an expired session needs a fresh
login first. Each run is a clean session — to report only new activity, save each
run's `collapsed.csv` (dated filename) and diff against the previous one.
