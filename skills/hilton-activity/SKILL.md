---
name: hilton-activity
description: Extract Hilton Honors activity into the unified points-activity CSV (Date, Description, Amount) plus the current balance. Use whenever the user wants to pull, export, check, sync, or monitor their Hilton Honors points history, stays, reward-night refunds, or credit-card earnings — including recurring/scheduled monthly checks. Triggers on "get my Hilton points", "export my Hilton Honors activity", "sync my Hilton points", "Hilton account activity". Part of the points-activity skill suite; scrapes the rendered activity page (12-month max; redemptions not exposed on web — see Caveats). Requires the user to be logged in to hilton.com in the connected Chrome browser — login is auto-detected via polling.
---
> **Unified output contract.** Part of `points-activity`. `scripts/transform.py` writes `Date, Description, Amount` and the filename `hilton_activity_<from>_<to>.csv` (covered range) via the shared `scripts/activity_output.py`, and prints `BALANCE:/COVERED:/REQUESTED:/FILE:/ROWS:` to stdout. The CSV is the deliverable; pushing it into a finance app is a separate, optional importer (see [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md)).

# Hilton Honors Activity Extraction

Reads the rendered activity page, walking all paginated pages. **Major caveat:**
redemptions (points spent on award stays) DO NOT appear on the web activity page — only
earnings and refunds. The mobile app shows redemptions; this is a known web glitch.

## Prerequisites
- **Claude in Chrome** connected (`list_connected_browsers` → `select_browser`).
- The skill never logs in for the user; the polling step waits up to ~4 min.

## The data source
Activity rows on `https://www.hilton.com/en/hilton-honors/guest/activity/` are
server-rendered. The site has a `/graphql/customer` endpoint but does not surface the
activity query through it for normal sessions — so DOM scrape it is. A row has: a
date-range header (`<Month> <D>, <YYYY> through … for N nights`), an activity/hotel name,
optionally `Confirmation #` (earn) or `Cancellation #` (refund), a trailing
`Points earned` / `Points refunded` label, and a signed-positive amount (`0` for pending
/ non-earning stays). History is capped at **12 months**.

## Procedure
1. **Open & wait for login (no prompt).** `navigate` to
   `https://www.hilton.com/en/hilton-honors/guest/activity/`, keep `tabId`, run
   `scripts/wait_for_login.js` (URL off `/login/` + `Total Points` + `Results X-Y of N`
   rendered, ≤4 min). Returns `{status:"logged-in", balance, total, waited_s}` or `{status:"timeout"}`.
2. **Scrape paginated activity.** Run `scripts/scrape_activity.js`: reads `Results X-Y of N`,
   parses visible rows, clicks **Next Page** and waits for the counter to advance, repeats
   until all pages are collected. Stashes merged rows on `window.__hhact`.
3. **Dump & read back.** Run `scripts/dump_console.js` (logs `HH###:`), then
   `read_console_messages(pattern:"^HH\\d", limit:60, tabId:...)`.
4. **Transform.** Strip the `HH###: ` prefix into `/tmp/raw.txt`, then
   `python3 scripts/transform.py /tmp/raw.txt <out_dir> [from] [to] [balance]`. Both
   `earn` and `refund` are positive credits; refund rows keep a `Refund - <hotel>`
   description. Zero-point rows drop out.
5. **Present.** `present_files` the CSV; report balance and covered range. **Expect the
   earnings sum to exceed the live balance** — every redemption is missing from the web
   feed, so do NOT treat sum==balance as a correctness check here.

## Classification
Card spend / partner credits / stays / refunds are all `kind='earn'` (positive credits),
collapsed by (date, description). There is no `redeem` on the web feed (see Caveats).

## Notes & quirks
- **No redemptions on web (confirmed glitch).** Only earnings and refunds list; award
  redemptions appear in the mobile app only. The CSV therefore over-states net unless a
  downstream consumer reconciles to the live balance.
- **12-month cap.** Hilton shows at most 12 months — older activity isn't available.
- **`Points earned: 0` stays** (pending, or award stays paid with points) drop at the zero filter.
- **"MEMBERSHIP REX UNITED STATES"** = Amex Membership Rewards → Hilton transfers.

## Recurring / scheduled use (monthly)
Run as a scheduled task on the user's own machine (needs the live Hilton session).
Save each run's CSV (dated filename) and diff to report only new activity.
