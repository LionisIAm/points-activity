---
name: aeroplan-activity
description: Extract Air Canada Aeroplan account points activity into the unified points-activity CSV (Date, Description, Amount) plus the current balance. Use whenever the user wants to pull, export, check, sync, or monitor their Aeroplan / Air Canada points history, transactions, reward bookings, or transfers — including recurring/scheduled monthly checks. Triggers on "get my Aeroplan points", "update my Aeroplan sheet", "Air Canada activity". Part of the points-activity skill suite; scrapes the dashboard (2-year max; Family Sharing caveat). Requires the user to be logged in to aircanada.com in the connected Chrome browser.
---
> **Unified output contract.** This sub-skill is part of `points-activity`. Its `scripts/transform.py` writes `Date, Description, Amount` and the filename `aeroplan_activity_<from>_<to>.csv` (covered range) via the shared `scripts/activity_output.py`, and prints `BALANCE:/COVERED:/REQUESTED:/FILE:/ROWS:` to stdout. The orchestrator passes the requested period and reads those lines. References to `collapsed.csv` / `Points` / `Miles` below are the older single-program wording; the actual columns are `Date, Description, Amount`.


# Air Canada Aeroplan Activity Extraction

Scrapes the rendered Aeroplan activity dashboard, sets the period filter to its max
(2 years), classifies and collapses, and outputs a points table.

## Prerequisites

- **Claude in Chrome** extension connected (`list_connected_browsers` → `select_browser`).
- User **logged in** to aircanada.com. Don't log in on their behalf.
- Verify login programmatically: a points balance shows top-right (e.g. "124,520 pts")
  and there are no sign-in buttons.

## Why DOM scraping (not the API)

Activity is served by an AWS AppSync GraphQL endpoint
(`akamai-gw.dbaas.aircanada.com/appsync/transaction-history-v2`). A plain fetch fails
(CORS / needs the Amplify client's auth), and the real request doesn't pass through
`window.fetch`/XHR so it can't be intercepted. The data renders into the normal light
DOM (Angular Material `mat-expansion-panel`), so scraping is the reliable path.

## ⚠️ Family Sharing caveat (read this)

If the account is a Family Sharing pool **lead**, the visible balance INCLUDES other
pool members, but the activity list shows only THIS account's transactions. Other
members' transfers/earns/returns are NOT here (e.g. a spouse's Chase transfer and some
return credits won't appear), even though they affect the shared balance. So:
**do not reconcile the activity total to the balance** — the mismatch is structural,
not an extraction error. Treat the output as "activity visible on this account".

## Procedure

### 1. Open the page
`tabs_context_mcp(createIfEmpty:true)` → `navigate` to
`https://www.aircanada.com/aeroplan/member/dashboard/activity`. Confirm login.
Decline the cookie banner ("Reject All") if present. Keep `tabId`.

### 2. Scrape (sets 2-year filter automatically)
Run `scripts/scrape_activity.js`. It opens Filters, selects "2 years" (the max
offered — 30/60/90 days, 6 months, 1 year, 2 years), applies, clicks any
"More"/"Load more" until the count stabilizes, then parses each
`<mat-expansion-panel>` header. Ad panels (e.g. "Earn points with Starbucks") have no
"Pts" and are skipped. Returns `{count}`, stashes rows on `window.__aero`.

Note: expanding a panel reveals a your-balance / other-pool-member split — we IGNORE
that and take only the header total (per requirements).

### 3. Dump and read back
Run `scripts/dump_console.js` (logs `AE###~ ...`), then
`read_console_messages(pattern:"^AE\\d", limit:60, tabId:...)`.

### 4. Transform
Strip the `AE###: ` prefix, write the `|`-delimited lines to a file
(e.g. `/tmp/raw.txt`), then:
```
python3 scripts/transform.py /tmp/raw.txt <output_dir> [from] [to] [balance]
# from/to are ISO yyyy-mm-dd or '-' for unbounded; balance is the current balance or omit.
```
Writes `collapsed.csv`, prints row count + points total.

### 5. Present
`present_files` on `collapsed.csv`. Don't reconcile to balance (see Family Sharing).

## The collapsed table (the deliverable)

`collapsed.csv`: columns `Date, Description, Points`. Logic (in `scripts/transform.py`):

1. **Classify**: *redemption* = Flight Reward Booking, its Cancellation, or an Aeroplan
   Family Sharing redemption (tied to a booking, matched to itineraries later);
   everything else (card transfers like Amex / Chase Ultimate Rewards, bonuses, partner
   earns) is an *earning/transfer*.
2. **Redemptions**: keep the real transaction date.
3. **Earnings/transfers**: move the date to the last day of its month.
4. **Collapse** by (Date, "Partner: Description"), sum Points. Identical rows on the
   same date merge (e.g. two equal Flight Reward Bookings → one summed row); rows that
   differ (e.g. cancellations carrying distinct transaction numbers) stay separate.
5. **Drop zero-point rows** after collapsing.

## Recurring / scheduled use (monthly)

Run as a **scheduled task on the user's own machine** — needs the user's real
Chrome + live Aeroplan session. Use the host's scheduling primitive: Cowork —
`mcp__scheduled-tasks__create_scheduled_task`; Claude Code — cron + headless
invocation. Caveats: local tasks run only while the computer is on and the app is
open; no completion/failure notifications yet; an expired session needs a fresh
login. Each run is a clean session — to report only new activity, save each run's
`collapsed.csv` (dated filename) and diff against the prior one. Note the 2-year
window: anything older than 2 years can never be retrieved, so a monthly cadence
is more than enough to never miss a transaction.
