---
name: points-activity
description: Extract loyalty points/miles account activity from any airline or hotel program into a unified CSV (Date, Description, Amount) plus the current balance. Use whenever the user asks to pull, export, check, sync, or monitor points/miles activity for a loyalty account — by program name (Hyatt, IHG, Accor, United, Aeroplan, Alaska, Marriott, Delta, Amex, etc.), by URL, or generically ("get my points activity for the last 6 months"). This is the ENTRY POINT and router; it delegates to a program-specific sub-skill when one exists, and falls back to general extraction when it doesn't.
---

# Points & Miles Activity — Orchestrator

Turns "get my <program> activity [for <period>]" into a unified
`<program>_activity_<from>_<to>.csv` (columns: **Date, Description, Amount**) plus the
**current balance**, for any airline/hotel loyalty program.

This skill is the router. It (1) figures out which program is meant, (2) delegates to
a known sub-skill if one exists, else (3) extracts using the general playbook below.

## The unified contract (every program obeys this)

- **Output CSV**: exactly three columns `Date, Description, Amount`. No Program column
  (the program is in the filename), no Unit column (points vs miles never mix in one
  file). `Date` is ISO `yyyy-mm-dd`. `Amount` is a signed integer (earn +, redeem −).
- **Filename**: `<program>_activity_<from>_<to>.csv`, where `<from>`/`<to>` are the
  ACTUAL covered range (oldest..newest row), not the requested range — so the name
  never overstates coverage. Written to the output dir.
- **Balance**: always also report the account's CURRENT balance alongside the file.
- **Collapsing rules** (shared across programs):
  - *Redemptions / flights / reward bookings* (things later matched to invoices or
    itineraries) → keep the REAL transaction date; each booking its own row.
  - *Earnings / transfers / bonuses* → keep the REAL transaction date; identical
    (date, description) rows are collapsed by summing.
  - Drop zero-amount rows after collapsing.
  - For a program with multiple point "currencies" (e.g. Accor reward vs status,
    United miles vs PQP), keep only the SPENDABLE currency (reward points / redeemable
    miles); ignore status/qualifying credits.
- **Sub-skills classify, the shared helper groups.** Each `transform.py` emits
  4-tuples `(date, description, amount, kind)` with `kind in {'earn','redeem'}`;
  `points-activity/scripts/activity_output.py` (`write_activity(...)`) owns the
  grouping (earn → collapse by (real date, description); redeem → each its own row)
  and also prints machine-readable `BALANCE:`, `COVERED:`, `REQUESTED:`, `FILE:`,
  `ROWS:` lines. Adding a program is parse-and-classify only — no per-program
  collapse logic. (3-tuples are still accepted and treated as `earn`.)

## Period handling

The user may ask for a period ("last 6 months", "since 2024", "everything"). Pass the
requested range to the sub-skill. Each program returns the **max available within that
request** and states honestly when the request is wider than what's retrievable:
- Hyatt, United: true date-range APIs — can honor arbitrary ranges (subject to history depth).
- Accor: full history (year accordions).
- IHG: only ~365 days exist — anything older is unavailable.
- Aeroplan: max 2 years; older can't be retrieved.
- Alaska: see its sub-skill (windowed).
Always report covered-vs-requested so the user knows if anything was truncated.

## Routing table (URL / name → sub-skill)

When the program is one of these, READ and EXECUTE that sub-skill's SKILL.md (Claude
doesn't "call" skills — it follows their steps):

| Program | Domain | Sub-skill | Method |
|---|---|---|---|
| World of Hyatt | hyatt.com | `hyatt-activity` | internal API (0-based paging) |
| IHG One Rewards | ihg.com | `ihg-activity` | DOM scrape (~365 days) |
| Accor ALL | all.accor.com | `accor-activity` | DOM scrape (expand year accordions) |
| United MileagePlus | united.com | `united-activity` | internal API (capture x-authorization-api) |
| Air Canada Aeroplan | aircanada.com | `aeroplan-activity` | DOM scrape (2-year filter; Family Sharing caveat) |
| Alaska Atmos Rewards | alaskaair.com | `alaska-activity` | DOM scrape (Shadow DOM; 24-month filter) |
| Bilt Rewards | bilt.com | `bilt-activity` | JSON API (month+year iteration; full history) |

If the user names a program with a sub-skill, prefer going straight to it. If they
give only a URL or a generic ask, match the domain above; if no match, use the general
playbook.

## General playbook (program with NO sub-skill)

Follow this to extract a new program, then consider writing a new sub-skill for it.

1. **Open & wait for login (no user prompt).** Navigate to the activity page in the
   connected Chrome, then run the sub-skill's `scripts/wait_for_login.js` via
   `javascript_tool`: it polls every ~3s for up to 4 minutes and returns
   `{status:"logged-in", ...}` or `{status:"timeout"}`. Detection is either an
   auth-gated API probe (API programs) or "URL not on a /sign-in path AND a balance
   value renders" (DOM programs). Only ask the user if it times out. Never log in for
   the user. Decline cookie banners (privacy).
2. **Find the data source — API first.** Read `performance.getEntriesByType('resource')`
   for backend hosts/paths matching activity|transaction|history|loyalty|points (filter
   out analytics/CDN). If an endpoint exists:
   - Try `fetch(url, {credentials:'include'})`. Common outcomes & fixes:
     - 401/403 → needs an auth header. Look in `localStorage` for a JWT; capture the
       real request's headers by hooking `XMLHttpRequest`/`fetch` and triggering a
       refetch (click a filter / "more"). Replay with the captured `Authorization` /
       `apiKey` / `x-authorization-api` / app-specific headers.
     - 405 → wrong method; the real call may be POST (often GraphQL/AppSync) — capture
       its method + body.
     - "Failed to fetch" → CORS; the SPA's own client adds headers a bare fetch lacks —
       capture the live request. If it's served by a client that bypasses
       `window.fetch`/XHR (Amplify, web worker), the API can't be intercepted — fall to
       DOM.
   - Note paging style (0-based vs 1-based offset — verify! a Hyatt-style off-by-one
     silently drops the newest page), page-size limits, and date params.
3. **DOM fallback.** If the API is unreachable, scrape the rendered table. Read each
   ROW container and pull fields from within it (don't zip three separate
   querySelectorAll arrays — header rows cause a one-row shift). Watch for:
   - **Shadow DOM** (web components, e.g. Alaska): recurse through `el.shadowRoot`.
   - **Accordions / lazy years** (e.g. Accor): click to expand collapsed sections first.
   - **Pagination** ("Show more"/"Load more"): click until the row count stabilizes.
   - **Ad rows** interleaved with data: skip rows lacking an amount.
4. **Export fallback.** If both are messy, look for "Export to excel" / "Download" /
   "Print" — often the cleanest full dump. Downloads require explicit user confirmation.
5. **Output via the contract.** Classify rows (redemption vs earning), collapse per the
   shared rules, and write through `scripts/activity_output.py:write_activity(...)`.
6. **Reconcile if possible.** If full history is visible, the spendable-currency sum
   should equal the balance — a good correctness check. Don't force it when the program
   only shows a window, or pools balances across members (Aeroplan Family Sharing).

## Reading a sub-skill's output

After running a sub-skill transform, parse its stdout: `BALANCE:`, `COVERED:`,
`REQUESTED:`, `FILE:`, `ROWS:`. Present the file with `present_files` and tell the user
the current balance and the covered range (flag truncation if COVERED is narrower than
REQUESTED).

## Helpers

- `scripts/activity_output.py` — the shared output contract (`write_activity`,
  `filter_by_period`). Every sub-skill transform imports it; keep its CSV schema and
  filename format stable, since changing it changes all programs at once.
