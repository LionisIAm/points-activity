---
name: example-import
description: TEMPLATE — copy this directory to skills/<app>-import/ and replace every TODO. Import a points-activity CSV into <App> via the <App> MCP. Use whenever the user wants to push, import, sync, or save loyalty points/miles activity INTO <App>. This is an IMPORTER (consumes the unified CSV a points-activity extractor produced). Requires the <App> MCP connected.
---
> **Importer · archetype: `api`/`mcp`.** Part of the `points-activity` suite — see
> [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md). Reads the unified CSV with
> `scripts/canonical_csv.py` and writes into <App>.

<!--
HOW TO USE THIS TEMPLATE
1. cp -R templates/import-skill skills/<app>-import
2. Set `name:` above to "<app>-import" (must equal the directory).
3. Keep scripts/canonical_csv.py VERBATIM (CI byte-diffs it against the canonical copy).
4. Fill the TODOs with your app's real MCP tool names. Use skills/finerd-import/ as the
   reference api/mcp implementation — but implement ONLY what your app's MCP supports.
5. If your app has no MCP write path, switch to a `file` archetype: emit an app-format
   CSV for manual upload instead (see ARCHITECTURE.md), and drop the MCP steps below.
6. Delete this comment block.
-->

# <App> Importer (points CSV → <App>)

## The one hard rule (mandatory for every importer)
**Never delete or destroy.** Create (and, where the app supports it, update in place);
never delete a transaction or remove user data — even auto-created phantoms, even when
re-syncing. If a cleanup seems necessary, surface it to the user and let them decide.

## Procedure
1. **Read the CSV.** `from canonical_csv import read_activity, parse_summary`:
   - `read_activity(csv_path)` → rows `{date, description, amount}` (amount signed:
     earn +, redeem −).
   - `parse_summary(extractor_stdout)` → `{balance, covered_from, covered_to, ...}`.
2. **Find/confirm the destination.** TODO: discover the account/holding for this program
   via the <App> MCP. Reuse an existing one; never create a duplicate.
3. **Map rows → <App> transactions.** TODO: translate each row to the <App> MCP's
   create shape. Decide the earn/redeem → credit/debit convention from <App>'s model.
   (Finerd maps earn→income accrual, redeem→expense — yours may differ.)
4. **Dedupe before writing.** TODO: query existing transactions; skip rows already
   present (match on date + amount + description). Idempotent re-runs are required.
5. **Reconcile (only if supported).** TODO: if <App> has a verified/true-balance concept,
   set it to `parse_summary(...)['balance']`; otherwise report the computed-vs-live delta.

## Notes & limitations
TODO: does <App> model a points/asset balance or only money? rate limits? whether it can
update in place or only create? Document what you implemented vs skipped.
