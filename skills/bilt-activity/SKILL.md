---
name: bilt-activity
description: Extract Bilt Rewards (Bilt Mastercard / Bilt points) account activity into the unified points-activity CSV (Date, Description, Amount) plus the current balance. Use whenever the user wants to pull, export, check, sync, or monitor their Bilt points history, rewards activity, earnings, or point transfers/redemptions to partners (World of Hyatt, American/AAdvantage, Alaska/Atmos, Accor, Flying Blue, British Airways/Avios, etc.) — including recurring/scheduled monthly checks. Triggers on "get my Bilt points", "update my Bilt activity", "Bilt rewards history", "Bilt Mastercard points". Part of the points-activity skill suite; uses Bilt's JSON API (full history). Requires the user to be logged in to bilt.com in the connected Chrome browser.
---

# Bilt Rewards Activity Extraction

> **Unified output contract.** Part of the `points-activity` suite. `scripts/transform.py`
> writes `Date, Description, Amount` and the filename `bilt_activity_<from>_<to>.csv`
> (covered range) via the shared `scripts/activity_output.py`, and prints
> `BALANCE:/COVERED:/REQUESTED:/FILE:/ROWS:` to stdout.

Bilt is a bank/card program: earnings are per-purchase (hundreds–thousands of rows),
redemptions are point transfers out to airline/hotel partners. We collapse earnings hard
(by month + benefit item) and keep redemptions per-transaction.

## Prerequisites

- **Claude in Chrome** connected (`list_connected_browsers` → `select_browser`).
- User **logged in** to bilt.com. Don't log in for them. Confirm the points balance shows
  in the header ("NN.Nk pts").

## Extraction — JSON API (not DOM)

Endpoint: `GET https://api.biltrewards.com/loyalty/activity?month=M&year=Y`
with header `authorization: Bearer <jwt>` (the JWT is in `localStorage` — scan for a long
value starting with `ey`). Plain `fetch(..., {credentials:'include'})` works.

**Only `month`+`year` filter.** `limit`, `page`, `from`/`to`, `startDate`/`endDate` are
all ignored (they return the default ~12 recent rows). So iterate months backward from the
current month until 3 consecutive empty months. Bilt has **no history-window limit** —
full account history is retrievable and reconciles to the balance.

## Procedure

1. **Open** `tabs_context_mcp` → `navigate` to `https://www.bilt.com/rewards/activity`.
   Confirm login + a points balance in the header. Decline cookie banners. Keep `tabId`.
2. **Fetch** run `scripts/fetch_activity.js` — finds the token, iterates months, stashes
   compacted entries on `window.__biltall`, returns `{count, oldest, newest, balanceCheck}`.
   `balanceCheck` should equal the displayed balance.
3. **Dump & read** run `scripts/dump_console.js` (emits `BILT###~<json-array>` chunks),
   then `read_console_messages(pattern:"^BILT\\d", limit:60, tabId:...)`. Reassemble the
   chunks in order and concatenate the arrays into a single JSON array file (e.g.
   `/tmp/raw.json`). (Large dumps: read in batches; chunks are ordered by their index.)
4. **Transform**
   ```
   python3 scripts/transform.py /tmp/raw.json <output_dir> [from] [to] [balance]
   # from/to ISO yyyy-mm-dd or '-'; balance = header "pts" figure.
   ```
5. **Present** `present_files` on the CSV. Report balance + covered range.

## Entry shape & the key rules

Compacted entry: `{d, t (title/merchant), a (activity), s (pointState), tp (totalPoints),
b: [{t (benefit item title), v (points int)}]}`.

- **Spendable points = `totalPoints`**, and `sum(b[].v) == totalPoints` (verified). The
  benefit items in `b` are the per-line points (e.g. "2X Points on All Transactions",
  "Additional 1X - Point Accelerator", "3x Points on Dining"). Cash-back "Earn Bilt Cash"
  (`+$…`) and non-point benefits are dropped (the fetch script keeps only point-bearing
  items — those whose value parses as a number, not a `$` amount).

- **Classify by SIGN, not status text** (robust to Bilt's vocabulary):
  - **Redemption** = any entry with `totalPoints < 0`. Transfers to partners (World of
    Hyatt, British Airways/Avios, Accor, Atmos, Flying Blue, …) and reversals/refunds.
    Keep the **real date**, each entry its **own row**, description = the title.
  - **Earning** = `totalPoints >= 0`. Explode into benefit **items** on the spend's
    **real date**, `kind='earn'`, no merchant in the title. The shared
    `activity_output.py` collapses identical `(date, item-title)` rows — so multiple
    "3x Points on Dining" on the **same day** merge; different days stay separate.

- Drop zero-amount rows after collapsing (status rows like "Earned Gold status" carry no
  points and disappear).

## Reconciliation

Full history is available, so `sum(Amount) == current balance` exactly (verified:
80,723 == 80.7k). If it doesn't reconcile, you likely stopped the month-iteration too
early (raise the empty-month threshold) rather than hitting a history limit.

## Recurring / scheduled use (monthly)

Run as a local Cowork Scheduled Task (needs the user's real Chrome + live bilt.com
session). The API token expires, so a stale session needs a fresh login. Because Bilt
keeps full history, a monthly cadence never misses anything; save each run's dated CSV and
diff to spot new activity. For incremental runs you can fetch only the current + previous
month rather than the full backfill.
