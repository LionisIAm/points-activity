# Contributing

The most useful contributions are **new loyalty programs**. Each program is a self-contained sub-skill under `skills/`.

## Adding a new program

### 1. Start from the template

```
cp -R templates/activity-skill skills/<program>-activity
```

The template is runnable as-is (a fake "Example Rewards" program) — run its test to
see the whole pipeline before you change anything:

```
cd skills/<program>-activity/tests && python3 test_transform.py
```

Set `name:` in `SKILL.md` to `<program>-activity` (must equal the directory). Then pick
ONE extraction path and delete the other:
- **API** (clean internal JSON): keep `scripts/fetch_activity.js`. Real-world auth
  references: `skills/hyatt-activity/` (simple) and `skills/united-activity/`
  (runtime-attached token via `capture_auth.js`).
- **DOM scrape** (no usable API): keep `scripts/scrape_activity.js`; see
  `skills/ihg-activity/` and `skills/accor-activity/`.

### 2. Find the data source

Open the program's activity page in Chrome with DevTools → Network tab open. Reload, scroll, or trigger filters. Look for XHR/fetch calls to backend hosts matching `activity|transaction|history|loyalty|points`. Filter out analytics/CDN noise.

For each candidate endpoint, note:
- Method (GET or POST — many GraphQL/AppSync endpoints are POST)
- URL pattern (including date params, pagination params)
- Pagination style — **verify 0-based vs 1-based** (off-by-one silently drops the newest page)
- Page-size limits
- Required headers (Bearer tokens, CSRF tokens, app-specific headers like `x-authorization-api`)
- Response shape

If a `fetch()` from console returns 401/403, the request needs an auth header the SPA attaches at runtime. Two patterns:
- **localStorage token**: read it directly (`localStorage.getItem('...')`) and add to fetch headers
- **runtime-attached token**: hook `XMLHttpRequest.prototype.setRequestHeader` to capture the header off a real request — see `skills/united-activity/scripts/capture_auth.js`

If the SPA bypasses `window.fetch`/XHR (Amplify, web worker, etc.), the API isn't interceptable — fall back to DOM scrape.

### 3. Write the scripts

Inside `skills/<program>-activity/scripts/`:

- **`wait_for_login.js`** — polls for login (API probe, or "URL not on /sign-in AND a balance renders"); returns `{status:"logged-in", ...}` or `{status:"timeout"}`. Poll ~3s for up to 4 min; only ask the user on timeout
- **`fetch_activity.js`** (API) or **`scrape_activity.js`** (DOM) — the actual extraction; stashes raw rows on `window.__<short>act` and returns `{count, oldest, newest}` (or `{error}`)
- **`dump_console.js`** — dumps stashed rows to console with a UNIQUE prefix (e.g. `HX###:` for Hyatt, `UA###:` for United). Direct JSON returns from `javascript_tool` are sometimes blocked by the chat — the console-dump path avoids this
- **`transform.py`** — parses console-dumped lines and **classifies** each row as `earn`/`redeem`, emitting 4-tuples `(date, description, amount, kind)`. It does NOT collapse — `activity_output.py` owns grouping. Keep only the spendable currency
- **`activity_output.py`** — the shared output contract. Ships in the template **verbatim**; do NOT edit it (CI byte-diffs every copy against the canonical `skills/points-activity/scripts/activity_output.py`)
- **`capture_auth.js`** (only if needed) — for runtime-attached auth headers

### 4. Write `SKILL.md`

- Description must include program name + common synonyms ("World of Hyatt", "Hyatt points", "Hyatt account activity") to trigger reliably
- Include the unified output contract header (copy from existing sub-skill)
- Document **API quirks** explicitly so future maintainers don't rediscover them the hard way (0-based pagination, broken `pageSize>=200`, etc.)
- Note any "Recurring / scheduled use" caveats

### 5. Update the orchestrator routing table

In `skills/points-activity/SKILL.md`, add a row to the program → sub-skill table with the program's domain.

### 6. Add trigger evals

In `skills/points-activity/evals/trigger_eval.json`, add **at least**:
- 2 positive cases (named program, URL-only)
- 2 near-miss cases that should NOT trigger your skill (e.g. "book a room at <hotel>", "fare rules PDF")

These guard against false positives — important because the skill takes over the browser.

### 7. Test end-to-end on your own account

Verify:
- Trigger fires from natural-language requests
- Login confirmation step works
- Output CSV matches the contract (columns, filename, collapsing rules)
- For full-history programs: `sum(amount where earn) − sum(amount where redeem) ≈ current balance` (reconciliation check)

### 8. Open a PR

Include:
- Sanitized sample output (no real account IDs, point balances, hotel names if private)
- A short note on what's tested vs untested
- Any caveats (Family Sharing pools, status currency, etc.)

## The unified output contract

Every program's `transform.py` calls:

```python
from activity_output import write_activity

write_activity(program, rows, out_dir,
               requested_from=None, requested_to=None, balance=None)
```

Where `rows` is a list of `(date_iso, description, amount_int, kind)` tuples with
`kind in {'earn', 'redeem'}`. The program classifies each row; `write_activity` does
the grouping (earn → collapse by (date, description); redeem → each its own row).
3-tuples `(date_iso, description, amount_int)` are still accepted and treated as `earn`.

The helper writes the CSV and prints machine-readable lines the orchestrator parses:

```
BALANCE: <int or "unknown">
COVERED: <from>..<to>
REQUESTED: <from>..<to> (or "all")
FILE: <path>
ROWS: <n>
```

**Do not diverge from this contract.** The orchestrator parses these lines literally; reordering or renaming breaks downstream consumers.

## Collapsing rules (shared across all programs)

- **Redemptions / flights / reward bookings** (things later matched to invoices/itineraries): keep the **real** transaction date; each booking gets its own row
- **Earnings / transfers / bonuses**: keep the **real** transaction date, then collapse identical `(date, description)` rows by summing
- **Drop zero-amount rows** after collapsing
- **Spendable currency only**: ignore status/qualifying currencies (United PQP, Accor status points, etc.)

## Code style

- **Python**: stdlib only — no external deps. Keep `transform.py` runnable as `python3 transform.py <raw_txt> <out_dir>`.
- **JS**: small, self-contained, no bundlers/builds. Modern syntax (ES2020+) is fine — Chrome supports it.
- **Comments**: preserve hard-won knowledge ("Pagination is 0-based — starting at 1 silently drops the newest page") rather than narrating the obvious.

## Testing without live accounts

Live API tests aren't possible in CI (would require a real loyalty account session). Instead, add:

- `skills/<program>-activity/tests/fixtures/raw_dump.txt` — sample console-dump lines (sanitized: fake IDs, fake amounts that still add up to a fake balance)
- `skills/<program>-activity/tests/test_transform.py` — pytest that runs `transform.py` against the fixture and asserts the expected CSV bytes

CI runs unit tests + lint. Smoke tests against live accounts are manual, run by maintainers before each release.

## Reporting a broken program

If a program's playbook stops working (API changed, page redesign, etc.), open an issue using the **"Playbook broken"** template. Include:
- Program name
- What you expected vs what happened
- Sanitized error message / console log
- If you can identify the API change (new endpoint shape, etc.), even better

## Maintainer review checklist

Before merging a new program:
- [ ] SKILL.md trigger description is specific enough (program name + synonyms)
- [ ] Trigger evals include near-miss negative cases
- [ ] Scripts have no hardcoded credentials, account IDs, or PII
- [ ] `activity_output.py` is unchanged (verbatim from existing sub-skill)
- [ ] No new dependencies (stdlib only)
- [ ] If `capture_auth.js` or any XHR/fetch hooking is added: code is reviewed line-by-line for safety
- [ ] Routing table in orchestrator is updated

Anything that hooks browser internals (XHR, fetch, headers, tokens) gets extra scrutiny — this is the highest-trust part of the codebase.
