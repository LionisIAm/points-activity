---
name: qatar-activity
description: Extract Qatar Airways Privilege Club (Avios) activity into the unified points-activity CSV (Date, Description, Amount) plus the current balance. Use whenever the user wants to pull, export, check, sync, or monitor their Qatar Airways / Privilege Club / Avios activity — including recurring/scheduled monthly checks. Triggers on "get my Qatar Avios", "export my Privilege Club activity", "sync my Qatar Airways points", "Privilege Club account activity". Part of the points-activity skill suite; scrapes the rendered activity table. Requires the user to be logged in to qatarairways.com in the connected Chrome browser — login is auto-detected via polling.
---
> **Unified output contract.** Part of `points-activity`. `scripts/transform.py` writes `Date, Description, Amount` and the filename `qatar_activity_<from>_<to>.csv` (covered range) via the shared `scripts/activity_output.py`, and prints `BALANCE:/COVERED:/REQUESTED:/FILE:/ROWS:` to stdout. The CSV is the deliverable; pushing it into a finance app is a separate, optional importer (see [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md)).

# Qatar Airways Privilege Club (Avios) Activity Extraction

Reads the rendered activity table on the "My activities" dashboard, keeps only spendable
**Avios** (Qpoints / Qcredits — both status-qualifying — are IGNORED), drops cancelled
redemptions, classifies and collapses via the shared helper.

## Prerequisites
- **Claude in Chrome** connected (`list_connected_browsers` → `select_browser`).
- The skill never logs in for the user; the polling step waits up to ~4 min.

## The data source
The page renders an HTML `<table>` with 8 columns:
```
Transaction date | Activity | Description | Company | Status | Avios | Qpoints | Qcredits
```
There is also an internal POST API
`https://eisffp.qatarairways.com/ffp-services/dashboardService/getActivities`
(body `{customerProfileId, ffpNumber, programCode:"QRPC", pageIndex, pageSize}`,
`Authorization: Bearer <rotating-token>`). It works inside the SPA but a bare
cross-origin `fetch` fails CORS preflight, so we rely on the rendered table (the SPA
pre-fetches the first page on load — usually the 10 most recent rows).

## Procedure
1. **Open & wait for login (no prompt).** `navigate` to
   `https://www.qatarairways.com/en/Privilege-Club/postLogin/dashboardqrpcuser/my-activities.html`,
   keep `tabId`, run `scripts/wait_for_login.js` (polls for the balance + activity table,
   ≤4 min). Returns `{status:"logged-in", balance, count, waited_s}` or `{status:"timeout"}`.
2. **Scrape.** Run `scripts/scrape_activity.js` → stashes normalized rows
   `{date, activity, description, company, status, avios}` on `window.__qract`; converts
   `DD Month YYYY` → ISO and parses signed Avios. It drops nothing — the transform does.
3. **Dump & read back.** Run `scripts/dump_console.js` (logs `QR###:`), then
   `read_console_messages(pattern:"^QR\\d", limit:120, tabId:...)`.
4. **Transform.** Strip the `QR###: ` prefix into `/tmp/raw.txt`, then
   `python3 scripts/transform.py /tmp/raw.txt <out_dir> [from] [to] [balance]`. Drops:
   **CANCELLED** redemptions (a paired refund row already models the net) and
   **Qpoints/Qcredits-only** rows (Avios == 0, not spendable).
5. **Present & reconcile.** `present_files` the CSV; report balance and covered range.
   The visible window is often only the 10 most recent rows — say so if COVERED is
   narrower than the user asked for.

## Classification
Negative Avios → `kind='redeem'` (award bookings, one row each); positive → `kind='earn'`
(refunds, partner transfers in, shopping earns — collapsed by (date, description)).

## Notes & quirks
- **Cancelled-redemption pairs.** A cancelled award leaves a "CANCELLED" redemption row
  AND a later "Refund - Award Cancellation(<id>)" row. We DROP the cancelled redemption
  and KEEP the refund — net effect is the original cost returned.
- **Short visible window.** Only ~10 most recent rows render by default. "View more"
  jumps to page 2 (often empty for low-volume accounts); the From/To date filter is in a
  popup this skill doesn't drive yet. Anything older isn't captured — report COVERED honestly.

## Limitations & future improvements
- **API path.** The endpoint works inside the SPA but a bare cross-origin fetch fails the
  CORS preflight (custom `Authorization` header). A future improvement: re-trigger the
  SPA's own XHR with a wide date range, capture the fresh Bearer token, and replay via
  `XMLHttpRequest`.

## Recurring / scheduled use (monthly)
Run as a scheduled task on the user's own machine (needs the live Privilege Club
session). Save each run's CSV (dated filename) and diff to report only new activity.
