---
name: copilot-import
description: Import a points-activity CSV into Copilot Money via the Copilot MCP. Use whenever the user wants to push, import, sync, or save loyalty points/miles activity INTO Copilot — e.g. "import my Hyatt points into Copilot", "sync my Alaska miles to Copilot Money". This is an IMPORTER (consumes the unified CSV that a points-activity extractor produced). Requires the Copilot MCP connected. SCAFFOLD — see TODOs before relying on it.
---
> **Importer · archetype: `api`/`mcp`.** Part of the `points-activity` suite — see
> [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md). Reads the unified CSV with
> `scripts/canonical_csv.py` and writes into Copilot via its MCP. The Finerd importer
> (`skills/finerd-import/`) is the reference api/mcp implementation — adapt its patterns
> to Copilot's actual MCP tools; implement only what Copilot supports.

# Copilot Money Importer (points CSV → Copilot)

> **STATUS: scaffold.** The pipeline shape is fixed; the Copilot-specific MCP calls
> are TODO. Fill them in against the live Copilot MCP tool names, then remove this note.

## The one hard rule
**Never delete or destroy.** Create (and, if Copilot supports it, update in place);
never delete a transaction or remove user data — even when re-syncing. If cleanup
seems needed, surface it to the user.

## Procedure
1. **Read the CSV.** `from canonical_csv import read_activity, parse_summary` — gives
   `{date, description, amount}` rows (amount signed: earn +, redeem −) plus the
   reported balance/covered range from the extractor's stdout.
2. **Find/confirm the destination in Copilot.** TODO: discover the account/holding for
   this loyalty program via the Copilot MCP. Reuse an existing one; don't duplicate.
3. **Map rows → Copilot transactions.** TODO: translate each CSV row to the Copilot MCP's
   create-transaction shape (date, name/merchant, amount, category). Decide the
   earn/redeem → credit/debit convention from Copilot's model.
4. **Dedupe before writing.** TODO: query existing transactions and skip rows already
   present (date + amount + description). If Copilot models only money (not a points
   asset), represent points as a custom asset or note the limitation to the user.
5. **Reconcile (only if Copilot supports it).** TODO: if there's a verified/true-balance
   concept, set it to the extractor's reported balance; else report the delta.

## Notes
- No external Python deps; `canonical_csv.py` is shared and must stay byte-identical to
  the canonical copy (CI enforces).
- If Copilot has no MCP write path for this data, consider a `file` archetype instead
  (emit a Copilot-format CSV for manual import) — see ARCHITECTURE.md.
