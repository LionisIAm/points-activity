---
name: flyingblue-activity
description: Extract Flying Blue (Air France-KLM) Miles activity into the unified points-activity CSV (Date, Description, Amount) plus the current balance. Use whenever the user wants to pull, export, check, sync, or monitor their Flying Blue / Air France / KLM Miles — including recurring/scheduled monthly checks. Triggers on "get my Flying Blue miles", "export my Air France activity", "sync my KLM miles", "Flying Blue account activity". Part of the points-activity skill suite; uses Flying Blue's internal JSON API. Requires the user to be logged in to flyingblue.com in the connected Chrome browser — login is auto-detected via polling.
---
> **Unified output contract.** Part of `points-activity`. `scripts/transform.py` writes `Date, Description, Amount` and the filename `flyingblue_activity_<from>_<to>.csv` (covered range) via the shared `scripts/activity_output.py`, and prints `BALANCE:/COVERED:/REQUESTED:/FILE:/ROWS:` to stdout. The CSV is the deliverable; pushing it into a finance app is a separate, optional importer (see [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md)).

# Flying Blue (Air France-KLM) Activity Extraction

Pulls full Flying Blue Miles activity via the dashboard's internal JSON API, keeps only
spendable **Miles** (XP — qualifying — is IGNORED), classifies and collapses via the
shared helper, and outputs a Miles table whose total reconciles to the live balance.

## Prerequisites
- **Claude in Chrome** connected (`list_connected_browsers` → `select_browser`).
- The skill never logs in for the user; the polling step waits up to ~4 min.

## The endpoint
```
GET https://www.flyingblue.com/kamino/me/transactions
```
- Session-cookie auth only — no token to capture. Returns the FULL on-file history in
  one call (no paging observed).
- Response: `{ summary: { miles: <int balance>, ... }, list: [ { date,
  description?, milesAmount (signed: − redemption / + earning), xpAmount (IGNORED),
  details: [ { date, description, milesAmount, xpAmount } ] } ] }`.
- `summary.miles` is the canonical live balance; the sum of `milesAmount` reconciles to it.

## Procedure
1. **Open & wait for login (no prompt).** `navigate` to
   `https://www.flyingblue.com/en/dashboard`, keep `tabId`, run
   `scripts/wait_for_login.js` (probes `/kamino/me/transactions` every 3s, ≤4 min).
   Returns `{status:"logged-in", balance, count, waited_s}` or `{status:"timeout"}`.
2. **Fetch + flatten.** Run `scripts/fetch_activity.js` → stashes flattened rows on
   `window.__fbact`, returns `{count, totalMilesSum, balance, oldest, newest}`. Flatten:
   - `milesAmount > 0` top-level → one **earn** row (top-level date+description).
   - `milesAmount < 0` top-level → one **redeem** row per `details[]` entry with
     `milesAmount != 0`, using `details.date` (the travel date, not the booking date).
   - `milesAmount == 0` → emit from `details` if their sum is non-zero; else skip
     (XP-only / not-yet-credited placeholder).
3. **Dump & read back.** Run `scripts/dump_console.js` (logs `FB###:`), then
   `read_console_messages(pattern:"^FB\\d", limit:60, tabId:...)`.
4. **Transform.** Strip the `FB###: ` prefix into `/tmp/raw.txt`, then
   `python3 scripts/transform.py /tmp/raw.txt <out_dir> [from] [to] [balance]`.
5. **Present & reconcile.** `present_files` the CSV; report the balance and covered
   range. The Miles total typically equals the current balance (full history fits one
   call).

## Classification
`scripts/transform.py` emits 4-tuples; the shared `activity_output.py` groups them:
negative `miles` → `kind='redeem'` (each award booking its own row, matched to
itineraries later); positive → `kind='earn'` (collapsed by (date, description)).
Zero-mile rows drop out.

## Notes & quirks
- **Future-dated redemptions.** Award tickets carry the booking date at the top level
  but the travel date in `details` — the flatten uses `details.date` so the CSV reflects
  when miles actually leave the account.
- **MILES+POINTS placeholders.** Some Accor MILES+POINTS rows post with `milesAmount: 0`
  (pending) and drop out at the zero filter.
- **Trip wrappers.** Multi-segment trips are one top-level row (earn) or expand to
  per-segment redemption rows (each passenger's reward ticket is its own row).

## Recurring / scheduled use (monthly)
Run as a scheduled task on the user's own machine (needs the live Flying Blue session).
Each run is a clean session — to report only new activity, save each run's CSV (dated
filename) and diff against the prior one.
