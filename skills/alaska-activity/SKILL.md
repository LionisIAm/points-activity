---
name: alaska-activity
description: Extract Alaska Atmos Rewards (Alaska Airlines / Mileage Plan) account points activity into the unified points-activity CSV (Date, Description, Amount) plus the current balance. Use whenever the user wants to pull, export, check, sync, or monitor their Alaska / Atmos Rewards points history, account activity, award flights, reward redemptions, or credit-card / partner earnings — including recurring/scheduled monthly checks. Triggers on "get my Alaska points", "update my Atmos sheet", "Alaska Airlines activity", "Mileage Plan activity". Part of the points-activity skill suite; scrapes the activity page (24-month max). Requires the user to be logged in to alaskaair.com in the connected Chrome browser.
---

# Alaska Atmos Rewards Activity Extraction

> **Unified output contract.** Part of the `points-activity` suite. `scripts/transform.py`
> writes `Date, Description, Amount` and the filename `alaska_activity_<from>_<to>.csv`
> (covered range) via the shared `scripts/activity_output.py`, and prints
> `BALANCE:/COVERED:/REQUESTED:/FILE:/ROWS:` to stdout.

Scrapes the rendered Atmos Rewards activity table (a web component / Shadow DOM), sets
the period filter to its max (24 months), loads all rows, classifies and collapses, and
outputs a points table.

## Prerequisites

- **Claude in Chrome** connected (`list_connected_browsers` → `select_browser`).
- User **logged in** to alaskaair.com. Don't log in for them. Confirm a balance shows
  ("Points balance: NNN,NNN") and there are no sign-in prompts.

## Why DOM scraping (not the API)

The activity API (`apis.alaskaair.com/.../accrueredeemmw/api/activities`) returns
"Failed to fetch" from page context — CORS, and the client doesn't route it through
`window.fetch`/XHR so it can't be intercepted. "Export to excel" is client-generated
from already-loaded rows (no new request, and only the loaded window) — not a full
solution. The table renders into a **Shadow DOM** web component, so we pierce shadow
roots and read it directly.

## Procedure

### 1. Open the page
`tabs_context_mcp(createIfEmpty:true)` → `navigate` to
`https://www.alaskaair.com/atmosrewards/account/activity`. If it redirects to the home
page, navigate again (the SPA sometimes bounces the first hit). Confirm login. Decline
cookie banners. Keep `tabId`.

### 2. Scrape (sets 24-month filter, loads all)
Run `scripts/scrape_activity.js`. It opens Filters, selects **Past 24 Months** (the max;
options are 3/6/12/24 months), applies, then clicks **Show More** until the row count
stabilizes. Parses rows by **structure** (see below). Returns `{count, oldest, newest}`,
stashes rows on `window.__akrows`.

### 3. Dump and read back
Run `scripts/dump_console.js` (logs `AK###~...`), then
`read_console_messages(pattern:"^AK\\d", limit:60, tabId:...)`.

### 4. Transform
Strip the `AK###~` prefix, write the `~`-delimited lines to a file (e.g. `/tmp/raw.txt`),
then:
```
python3 scripts/transform.py /tmp/raw.txt <output_dir> [from] [to] [balance]
# from/to ISO yyyy-mm-dd or '-'; balance is the "Points balance:" figure.
```

### 5. Present
`present_files` on the CSV. Report balance + covered range.

## Columns & the key rules

The table has 7 columns:
`Date | Activity | Status | Points | Bonus points | Total points | Status points`

- **Spendable currency = "Total points"** (index 5). **"Status points"** (index 6) is
  elite-qualifying and is dropped — never mix it in.
- **Capture everything structurally, NOT by a status whitelist.** A row is a transaction
  iff cell 0 is a date and cell 5 (Total points) is numeric. Do **not** filter by status
  text — Atmos uses `Credited`, `Redeemed`, `Redeposited` (award reversals/"Rollback:"),
  and possibly others; a whitelist silently drops statuses you didn't list. (This was a
  real bug: filtering `Credited|Redeemed|Pending` dropped `Redeposited` rollback rows and
  made the balance fail to reconcile by exactly the reversed amount.)

## Collapsing (in `transform.py`)

1. **Classify** (robust, not status-based): a row is a *redemption* if Total points is
   negative OR the Activity carries an award/booking marker (a flight route like
   `BCN-SFO`, `Rollback:`, or Reward/Award/Redemption/Redeposit). Otherwise it's an
   *earning/transfer*.
2. **Redemptions** keep the real date; each row stays separate (per passenger; a reversal
   is its own row) so a change/rebook nets out per-leg and rows match itineraries.
3. **Earnings/transfers** → keep real date, `kind='earn'`; shared `activity_output.py` collapses identical (date, description).
4. **Drop zero-Total rows** after collapsing.
5. Do **not** case-normalize descriptions: Atmos genuinely lists some award rows twice
   with different name casing — those are real separate transactions.

## Reconciliation

When the full window is captured, `sum(Total points) == Points balance` (verified:
balance reconciled exactly once `Redeposited` rows were included). If it doesn't
reconcile, suspect a missed status (re-check the structural filter) before assuming the
gap is pre-window history. Note the **24-month limit**: genuinely older accruals can't be
retrieved, in which case reconciliation legitimately won't close.

## Recurring / scheduled use (monthly)

Run as a local Cowork Scheduled Task (needs the user's real Chrome + live Atmos session).
Caveats: runs only while the machine is on and the app open; no completion notifications;
expired session needs fresh login. Save each run's dated CSV and diff to spot new
activity. The 24-month window means a monthly cadence never misses anything.
