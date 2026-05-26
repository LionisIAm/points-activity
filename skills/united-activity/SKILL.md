---
name: united-activity
description: Extract United MileagePlus account miles activity into the unified points-activity CSV (Date, Description, Amount) plus the current balance. Use whenever the user wants to pull, export, check, sync, or monitor their United / MileagePlus miles history, account activity, flights, award miles, or credit-card earnings — including recurring/scheduled monthly checks. Triggers on "get my United miles", "update my MileagePlus sheet", "United account activity". Part of the points-activity skill suite; uses United's internal API. Requires the user to be logged in to united.com in the connected Chrome browser.
---
> **Unified output contract.** This sub-skill is part of `points-activity`. Its `scripts/transform.py` writes `Date, Description, Amount` and the filename `united_activity_<from>_<to>.csv` (covered range) via the shared `scripts/activity_output.py`, and prints `BALANCE:/COVERED:/REQUESTED:/FILE:/ROWS:` to stdout. The orchestrator passes the requested period and reads those lines. References to `collapsed.csv` / `Points` / `Miles` below are the older single-program wording; the actual columns are `Date, Description, Amount`.


# United MileagePlus Activity Extraction

Pulls full MileagePlus activity via United's internal JSON API, keeps only MILES,
classifies and collapses it, and outputs a miles table whose total reconciles to the
mileage balance.

## Prerequisites

- **Claude in Chrome** extension connected (`list_connected_browsers` → `select_browser`).
- User **logged in** to united.com. Don't log in on their behalf.
- Verify login programmatically: the activity page shows a mileage balance (e.g.
  "107,409 miles") and no sign-in buttons.

## The endpoint

```
GET https://www.united.com/api/myunited/account/Activities/StartDate=YYYY-MM-DD~EndDate=YYYY-MM-DD/<limit>
```
- Date-bounded window + row `<limit>`. Use a wide start (e.g. 2018-01-01), end = today,
  limit 500 → everything in one call.
- Response: `{ data: { activities: [...] } }`. Each activity: `ActivityType` ('F' =
  flight, 'O' = other/earning), `Description`, `TransactionDate`, `TotalMiles` (final
  amount, already includes all bonus components), plus `PQP/PQF/PQS` (Premier-
  qualifying — IGNORED here), `IsRedeposit`, `PartnerName`.

### Auth — the critical bit
A plain GET returns **405**. The request needs header `x-authorization-api: bearer
<token>`. That token is NOT in localStorage — the SPA attaches it at runtime, so it
must be captured from a real request the page makes. (This is why the skill has a
capture step; a fresh token is needed each session.)

## Procedure

### 1. Open the page
`tabs_context_mcp(createIfEmpty:true)` → `navigate` to
`https://www.united.com/en/us/account/activity`. Confirm login. Keep `tabId`.

### 2. Capture the auth token
Run `scripts/capture_auth.js` (arms an XHR hook). Then trigger a real activity
re-fetch so the hook catches the header — click the "Recent activity" control, or
"Collapse all rows" / "Expand all rows", e.g.:
```js
[...document.querySelectorAll('button,a')].find(b=>/recent activity|collapse all rows|expand all rows/i.test(b.textContent||''))?.click()
```
Wait ~2s, then confirm `window.__unitedAuth.xAuth` is set (re-run capture_auth.js — it
reports `alreadyCaptured`). If the page throws "Cannot access a chrome-extension://
URL", a foreign extension node is interfering — re-`navigate` to the activity URL and
retry.

### 3. Fetch
Run `scripts/fetch_activity.js`. Returns `{count, totalMilesSum, oldest, newest}` and
stashes activities on `window.__uact`. If it reports a stale-token/HTTP error, redo
step 2.

### 4. Dump and read back
Run `scripts/dump_console.js` (logs `UA###~ ...`), then
`read_console_messages(pattern:"^UA\\d", limit:60, tabId:...)`. (Direct JSON returns
are often blocked by the chat — the console path avoids it.)

### 5. Transform
Strip the `UA###: ` prefix, write the `~~`-delimited lines to a file
(e.g. `/tmp/raw.txt`), then:
```
python3 scripts/transform.py /tmp/raw.txt <output_dir> [from] [to] [balance]
# from/to are ISO yyyy-mm-dd or '-' for unbounded; balance is the current balance or omit.
```
Writes `collapsed.csv`, prints row count + miles total.

### 6. Present and sanity-check
`present_files` on `collapsed.csv`. The miles total may equal the current mileage
balance (true when the full history fits the window) — a good check, but don't force
it if older activity has rolled off.

## The collapsed table (the deliverable)

`collapsed.csv`: columns `Date, Description, Miles` (Miles = TotalMiles only;
PQP/PQF/PQS ignored). Logic (in `scripts/transform.py`):

1. **Classify** by ActivityType: 'F' = flight (like a hotel "stay"); everything else =
   earning/transfer.
2. **Flights**: keep the real transaction date; each its own row (matched to
   itineraries later); flight number + route kept in the description.
3. **Earnings/transfers**: move the date to the last day of its month so repeated
   monthly card-earn lines collapse.
4. **Collapse** by (Date, Description), sum miles.
5. **Drop zero-mile rows** after collapsing (PQP-only rows fall out).

## Recurring / scheduled use (monthly)

Run as a **local Cowork Scheduled Task** (needs the user's real Chrome + live United
session, and a freshly-captured token each run). Caveats: local tasks run only while
the computer is on and the app is open; no completion/failure notifications yet; an
expired session needs a fresh login. Each run is a clean session — to report only new
activity, save each run's `collapsed.csv` (dated filename) and diff against the prior one.
