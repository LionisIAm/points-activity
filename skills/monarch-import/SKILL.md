---
name: monarch-import
description: Import a points-activity CSV into Monarch Money via the Monarch MCP. Use whenever the user wants to push, import, sync, or save loyalty points/miles activity INTO Monarch — e.g. "import my Hyatt points into Monarch", "sync my Bilt activity to Monarch Money". This is an IMPORTER (consumes the unified CSV that a points-activity extractor produced). Requires the Monarch MCP connected. SCAFFOLD — see TODOs before relying on it.
---
> **Importer · archetype: `api`/`mcp`.** Part of the `points-activity` suite — see
> [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md). Reads the unified CSV with
> `scripts/canonical_csv.py` and writes into Monarch via its MCP. The Finerd importer
> (`skills/finerd-import/`) is the reference api/mcp implementation — adapt its patterns
> to Monarch's actual MCP tools; implement only what Monarch supports.

# Monarch Money Importer (points CSV → Monarch)

> **STATUS: scaffold.** The pipeline shape is fixed; the Monarch-specific MCP calls
> are TODO. Fill them in against the live Monarch MCP tool names, then remove this note.

## The one hard rule
**Never delete or destroy.** Create (and, if Monarch supports it, update in place);
never delete a transaction or remove user data — even when re-syncing. If cleanup
seems needed, surface it to the user.

## Procedure
1. **Read the CSV.** `from canonical_csv import read_activity, parse_summary` — gives
   `{date, description, amount}` rows (amount signed: earn +, redeem −) plus the
   reported balance/covered range from the extractor's stdout.
2. **Find/confirm the destination in Monarch.** TODO: discover the account/holding that
   represents this loyalty program via the Monarch MCP (list accounts / search). Do not
   create duplicates; reuse an existing one.
3. **Map rows → Monarch transactions.** TODO: translate each CSV row to the Monarch
   MCP's create-transaction shape (date, merchant/description, amount, category). Decide
   the earn/redeem → credit/debit convention from what Monarch's model expects.
4. **Dedupe before writing.** TODO: query existing transactions on the destination and
   skip rows already present (match on date + amount + description). Monarch may or may
   not expose a points/asset concept — if it only models money, represent points as a
   custom asset/holding or note the limitation to the user.
5. **Reconcile (only if Monarch supports it).** TODO: if Monarch has a verified/true
   balance concept, set it to the extractor's reported balance so any gap is corrected;
   otherwise report the computed-vs-live delta to the user.

## Notes
- No external Python deps; `canonical_csv.py` is shared and must stay byte-identical to
  the canonical copy (CI enforces).
- If Monarch has no public/MCP write path for this data, consider a `file` archetype
  instead (emit a Monarch-format CSV for manual upload) — see ARCHITECTURE.md.
