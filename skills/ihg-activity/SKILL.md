---
name: ihg-activity
description: Extract IHG One Rewards account points activity into the unified points-activity CSV (Date, Description, Amount) plus the current balance. Use whenever the user wants to pull, export, check, sync, or monitor their IHG points history, account activity, stays, reward-night redemptions, or credit-card points — including recurring/scheduled monthly checks. Triggers on "get my IHG points activity", "update my IHG sheet", "IHG account activity". Part of the points-activity skill suite; scrapes the rendered activity table (~365 days). Requires the user to be logged in to ihg.com in the connected Chrome browser.
---
> **Unified output contract.** This sub-skill is part of `points-activity`. Its `scripts/transform.py` writes `Date, Description, Amount` and the filename `ihg_activity_<from>_<to>.csv` (covered range) via the shared `scripts/activity_output.py`, and prints `BALANCE:/COVERED:/REQUESTED:/FILE:/ROWS:` to stdout. The orchestrator passes the requested period and reads those lines. References to `collapsed.csv` / `Points` / `Miles` below are the older single-program wording; the actual columns are `Date, Description, Amount`.


# IHG One Rewards Account Activity Extraction

Scrapes the rendered IHG account-activity table, classifies and collapses it, and
outputs a points table. IHG only exposes ~365 days (~30 rows) of activity, and that
is the full available history — there is no deeper archive to page through.

## Prerequisites

- **Claude in Chrome** extension connected (`list_connected_browsers` → `select_browser`).
- User **logged in** to ihg.com. IHG sessions drop quickly and redirect to a sign-in
  page; the skill must not log in on the user's behalf.
- Verify login programmatically: the activity page shows the point balance (e.g.
  "161,045 pts") and no sign-in buttons. If the URL contains `/sign-in`, stop and ask
  the user to log in.

## Why DOM scraping (not the API)

The data API `apis.ihg.com/members/v1/profiles/me/activities` needs an `apikey`
(in `window.APIGEE_APIKEY_VALUE`) plus the `X-IHG-SSO-TOKEN` header set; a plain
`fetch` reproducing them still returns 504, and the Angular app doesn't use
`window.fetch`/patchable XHR so the live request can't be intercepted reliably. Since
the page only ever shows ~365 days anyway, scraping the rendered table is simpler and
complete. (Endpoint shape, if ever revisited: `?activityType=all&duration=365&limit=10&offset=N`, 0-based offset.)

## Procedure

### 1. Open the page
`tabs_context_mcp(createIfEmpty:true)` → `navigate` to
`https://www.ihg.com/rewardsclub/us/en/account-mgmt/activity`. Confirm login (see
above). Keep the `tabId`.

### 2. Scrape
Run `scripts/scrape_activity.js` via `javascript_tool` (action `javascript_exec`).
It scrolls to load all rows, parses each table `<tr>`, returns `{count, newest,
oldest}`, and stashes rows on `window.__ihg`.

If a previous run left a foreign browser-extension node in the page, a global
`querySelectorAll` can throw "Cannot access a chrome-extension:// URL". If that
happens, re-`navigate` to the activity URL (fresh load clears it) and re-run.

### 3. Dump and read back
Run `scripts/dump_console.js` (logs `IX###~ ...` lines), then
`read_console_messages(pattern:"^IX\\d", limit:60, tabId:...)`. Direct JSON returns
are often blocked by the chat ("Cookie/query string data"); the console path avoids it.

### 4. Transform
Strip the `IX###: ` prefix from each line, write the remaining `~~`-delimited lines
to a file (e.g. `/tmp/raw.txt`), then run:
```
python3 scripts/transform.py /tmp/raw.txt <output_dir> [from] [to] [balance]
# from/to are ISO yyyy-mm-dd or '-' for unbounded; balance is the current balance or omit.
```
It writes `collapsed.csv` and prints row count + total.

### 5. Present
`present_files` on `collapsed.csv`. Do NOT reconcile against the balance — the
activity sum will not equal it (only ~365 days are shown). That mismatch is expected.

## The collapsed table (the deliverable)

`collapsed.csv`: columns `Date, Description, Points`. Logic (all in
`scripts/transform.py` — read its docstring before editing):

1. **Classify** each row as a *redemption* ("Redeemed points for Reward Night stay on
   MM/DD/YYYY ...") or an *earning/transfer* (everything else).
2. **Redemptions:** keep the real transaction date; strip the per-night date from the
   description so all nights of one booking collapse into ONE Stay row (a 4-night
   reward booking 0 / -45,000 / -42,000 / -45,000 → one -132,000 row). Real date kept
   because redemptions get matched to invoices later.
3. **Earnings/transfers:** move the date to the last day of its month, so repeated
   monthly items collapse together.
4. **Collapse** by (Date, normalized Description), sum Points. Brand + hotel after
   ' | ' are KEPT (used to match reservations later).
5. **Drop zero-point rows** — but only AFTER collapsing, so a 0-point free night still
   merges into its booking first.

## Recurring / scheduled use (monthly)

Run as a **local Cowork Scheduled Task** (needs the user's real Chrome + live IHG
session, which only exist on their machine). Caveats for the user: local tasks run
only while the computer is on and the app is open; no completion/failure
notifications yet; a month-old IHG session will almost always need a fresh login
first. Each run is a clean session — to report only new activity, save each run's
`collapsed.csv` (dated filename) and diff against the previous one.
