---
name: hyatt-activity
description: Extract World of Hyatt account points activity into the unified points-activity CSV (Date, Description, Amount) plus the current balance. Use whenever the user wants to pull, export, check, sync, or monitor their Hyatt points history, account activity, stays, bonuses, or award redemptions — including recurring/scheduled monthly checks. Triggers on "get my Hyatt points activity", "update my Hyatt sheet", "Hyatt account activity". Part of the points-activity skill suite; uses Hyatt's internal API. Requires the user to be logged in to hyatt.com in the connected Chrome browser.
---
> **Unified output contract.** This sub-skill is part of `points-activity`. Its `scripts/transform.py` writes `Date, Description, Amount` and the filename `hyatt_activity_<from>_<to>.csv` (covered range) via the shared `scripts/activity_output.py`, and prints `BALANCE:/COVERED:/REQUESTED:/FILE:/ROWS:` to stdout. The orchestrator passes the requested period and reads those lines. References to `collapsed.csv` / `Points` / `Miles` below are the older single-program wording; the actual columns are `Date, Description, Amount`.


# Hyatt Account Activity Extraction

Pulls full World of Hyatt account-activity history via Hyatt's internal JSON API
(no DOM scraping, no "Load More" clicking, no chevron expanding), normalizes it,
and outputs a collapsed points table whose total equals the account balance.

## Prerequisites

- **Claude in Chrome** extension connected (`list_connected_browsers` → `select_browser`).
- User **logged in** to hyatt.com. The API relies on the live session cookie; the
  skill cannot and must not log in on the user's behalf.
- Sessions expire fairly quickly. On a scheduled run, if the fetch returns an error
  or zero rows, stop and ask the user to log in — do not retry blindly.

## Procedure

### 1. Open the page
`tabs_context_mcp(createIfEmpty:true)` → `navigate` the tab to
`https://www.hyatt.com/profile/en-US/account-activity`. Ask the user to confirm
they're logged in (skip if already confirmed this session). Keep the `tabId`.

### 2. Fetch all transactions
Run `scripts/fetch_activity.js` via `javascript_tool` (action `javascript_exec`) in
that tab. It returns `{count, oldest, newest}`. Sanity-check `newest` is recent —
if it's months stale, something dropped the first page (see API quirks below).

If it returns `{error: ...}`, the user is almost certainly not logged in. Stop and ask.

### 3. Dump rows to console and read them back
Returning the raw array directly is often **blocked by the chat** ("Cookie/query
string data"). Instead:
- Run `scripts/dump_console.js` (logs one `HX###~...` line per transaction).
- Read them with `read_console_messages(pattern:"^HX\\d", limit:200, tabId:...)`.

### 4. Transform
Strip the `HX###~` prefix from each line, write the remaining tilde-delimited lines
to a file (e.g. `/tmp/raw.txt`), then run:
```
python3 scripts/transform.py /tmp/raw.txt <output_dir> [from] [to] [balance]
# from/to are ISO yyyy-mm-dd or '-' for unbounded; balance is the current balance or omit.
```
It writes `normalized.csv` (full, all components, all types — keep for auditing)
and `collapsed.csv` (the deliverable), and prints the points sum.

### 5. Verify and present
The printed **points sum must equal the account's current balance** (visible on the
page, top-left "Current Point Balance"). If it matches, present `collapsed.csv` with
`present_files`. If it does NOT match, do not silently ship it — report the mismatch;
something in the API shape likely changed (see below).

## The collapsed table (the deliverable)

`collapsed.csv`: columns `Date, Component, Points`. Produced by:
1. Normalize every transaction into one row per point-bearing component.
2. Keep only real points rows (PointsType `P`); drop night credits (`N`).
3. For every category **except AWARD**, move the date to the **last day of its month**;
   AWARD keeps its real date.
4. Group by `(Date, Component)`, sum `Points`.

All the reasoning lives in `scripts/transform.py` — read its docstring before editing.

## API quirks (do not rediscover these the hard way)

- **Endpoint:** `GET https://www.hyatt.com/profile/api/stay/pastactivity?pageSize=15&pageIndex=N&transactionType=&locale=en-US&startDate=&endDate=`
- **Pagination is 0-BASED.** `pageIndex=0` is the NEWEST page. Starting at 1 silently
  drops the most recent ~15 transactions — the single most likely bug.
- **Large pageSize breaks:** `pageSize>=200` returns `[]`. Use 15.
- **Stop condition:** response field `showLoadMoreButton === false`.
- **Field semantics:** points live in `totalAmount` for BONUS/AWARD/PARTNER_EARN; for
  STAY use `baseAmount` + each `bonusDetail` item (the STAY `totalAmount` can be wrong).
- **bonusDetail** holds the nested point-bearing components (Globalist bonus, Double
  Points, promos). These must each become their own row.
- AWARD and PARTNER_EARN can have a blank `pointsType` yet still move points — count
  them when `totalAmount != 0`.

## Recurring / scheduled use (monthly)

Best run as a **scheduled task on the user's own machine** — it needs the user's
real Chrome with a live Hyatt session, which only exists locally, so a cloud
routine won't work. Use whichever scheduling primitive the host provides — Cowork:
`mcp__scheduled-tasks__create_scheduled_task`; Claude Code: cron + headless
invocation. Note for the user: local scheduled tasks run only while the computer
is on and the app is open, there are no completion/failure notifications yet, and
a month-old session will usually need a fresh login before the run. Each run is a
clean session, so to report only *new* activity, save each run's `collapsed.csv`
(e.g. dated filename) and diff against the previous one rather than re-reporting
all rows.
