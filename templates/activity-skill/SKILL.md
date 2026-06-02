---
name: example-activity
description: TEMPLATE — copy this directory to skills/<program>-activity/ and replace every TODO. Update the user's <Program> (<currency>) activity in Finerd-agnostic CSV form — extract the history from <domain> and write the unified Date,Description,Amount CSV. Use whenever the user wants to update, sync, refresh, pull, or check their <Program> points/miles. Triggers on "update my <Program> activity", "sync my <Program> points", "<Program> account activity". Part of the points-activity skill suite. Requires the user to be logged in to <domain> in the connected Chrome browser — auto-detected via polling, no need to ask.
---
> **Unified output contract.** This sub-skill is part of `points-activity`. Its `scripts/transform.py` writes `Date, Description, Amount` and the filename `<program>_activity_<from>_<to>.csv` (covered range) via the shared `scripts/activity_output.py`, and prints `BALANCE:/COVERED:/REQUESTED:/FILE:/ROWS:` to stdout. The orchestrator passes the requested period and reads those lines.

<!--
============================================================================
HOW TO USE THIS TEMPLATE
1. cp -R templates/activity-skill skills/<program>-activity
2. Rename the skill: set `name:` above to "<program>-activity" (must match dir).
3. Pick ONE extraction path and delete the other:
   - API available  -> keep scripts/fetch_activity.js, delete scrape_activity.js
   - DOM scrape only -> keep scripts/scrape_activity.js, delete fetch_activity.js
4. Fill in scripts/wait_for_login.js, the chosen extractor, dump_console.js,
   transform.py. Keep scripts/activity_output.py VERBATIM (CI byte-diffs it).
5. Replace tests/fixtures/raw_dump.txt with a SANITIZED sample (fake ids/amounts
   that still sum to a fake balance) and update tests/test_transform.py.
6. Register: add a row to skills/points-activity/SKILL.md routing table and the
   README "Supported programs" table. (tests/test_registration.py enforces the
   routing-table row.)
7. Delete this comment block.
The fake "Example Rewards" content below is runnable as-is so you can run the
test before adapting:  cd skills/example-activity/tests && python3 test_transform.py
============================================================================
-->

# <Program> Activity Extraction

TODO one-paragraph summary: where the data comes from (API endpoint or rendered
table), which currency is SPENDABLE (ignore status/qualifying currencies), and
whether the full history reconciles to the balance or only a window is available.

## Prerequisites
- **Claude in Chrome** extension connected (`list_connected_browsers` → `select_browser`).
- The skill never logs in for the user; the polling step waits up to ~4 min.

## Procedure
1. **Open & wait for login (no user prompt).** Navigate to `<activity URL>`, keep
   `tabId`, run `scripts/wait_for_login.js`. It returns `{status:"logged-in", ...}`
   or `{status:"timeout"}` — only ask the user on timeout.
2. **Extract.** Run `scripts/fetch_activity.js` (API) or `scripts/scrape_activity.js`
   (DOM). It stashes raw rows on `window.__<short>act` and returns `{count, ...}`.
   - **API auth quirks**: 401/403 → header the SPA attaches; capture via XHR hook.
     405 → real call is probably POST. "Failed to fetch" → CORS; replay the live
     request. **Verify 0-based vs 1-based paging** — the #1 silent off-by-one bug.
3. **Dump & read back.** Run `scripts/dump_console.js` (logs `XX###: ...`), then
   `read_console_messages(pattern:"^XX\\d", ...)`. (Direct JSON returns are often
   blocked by the chat — the console path avoids it.)
4. **Transform.** `python3 scripts/transform.py /tmp/raw.txt <out_dir> [from] [to] [balance]`
   → writes `<program>_activity_<from>_<to>.csv`.
5. **Present** the CSV and report BALANCE/COVERED. (Pushing the CSV into a finance
   app is a separate **importer** skill — extractors stay app-agnostic.)

## Classification (the only per-program logic you write)
Emit 4-tuples `(date, description, amount, kind)`. The shared
`activity_output.py` does ALL grouping — you never collapse yourself:
- `kind='redeem'` — redemptions / award bookings / transfers-out / reversals.
  Each keeps its **real date** and stays its **own row** (matched to itineraries
  later).
- `kind='earn'` — stays, card spend, bonuses, partner earns. Collapsed by
  `(real date, description)` summed.
- Keep only the **spendable** currency; drop status/qualifying credits.
- Zero-amount rows are dropped by the shared helper.

## Notes & quirks (preserve hard-won knowledge here)
TODO: pagination style, session-expiry behavior, Shadow DOM, accordions,
family-sharing pooling (don't force reconciliation), etc.
