# Architecture

`points-activity` is built from two kinds of skill, joined by one stable boundary:
a **unified CSV**. Keeping the boundary fixed is what lets each side evolve — and be
contributed to — independently.

```
   loyalty program                 unified CSV                    finance app
  ┌───────────────┐   browser   ┌──────────────┐   (optional)  ┌──────────────┐
  │ hyatt.com,    │ ──────────▶ │ Date,        │ ────────────▶ │ Finerd,      │
  │ united.com,   │  EXTRACTOR  │ Description, │   IMPORTER     │ Monarch,     │
  │ qatarairways… │ *-activity  │ Amount       │  *-import      │ Copilot…     │
  └───────────────┘             └──────────────┘               └──────────────┘
         the 90% contribution surface          opt-in, one per destination app
```

The orchestrator skill (`points-activity`) routes a request to the right extractor.
It **ends at the CSV by default**. Only if the user asks to push into a finance app —
and the matching importer is installed — does it hand the CSV to that importer.

## Role 1 — Extractor (`<program>-activity`)

Produces the unified CSV for one loyalty program from the user's own logged-in
browser session. This is where almost all contributions land. An extractor:

- drives only the browser (Claude in Chrome MCP) — never logs in for the user;
- classifies each row as `earn` or `redeem` and emits 4-tuples
  `(date, description, amount, kind)`;
- writes via the shared `activity_output.py:write_activity(...)`, which owns ALL
  grouping (earn → collapse by `(date, description)`; redeem → one row each) and
  prints the machine-readable `BALANCE:/COVERED:/REQUESTED:/FILE:/ROWS:` lines.

An extractor **knows nothing about any finance app.** Start from
`templates/activity-skill/`. Full spec: [CONTRIBUTING.md](../CONTRIBUTING.md).

## Role 2 — Importer (`<app>-import`)

Consumes the unified CSV and writes it into one destination app. Opt-in: installed
only by users of that app. An importer reads the CSV with the shared
`canonical_csv.py` and then does whatever its destination needs.

### Archetypes

| Archetype | How it writes | Examples | Destructive risk |
|---|---|---|---|
| `api` / `mcp` | Calls the app's API/MCP to create transactions directly | `finerd-import`, `monarch-import`, `copilot-import` | real — see the one hard rule |
| `file` | Emits an app-format CSV the user uploads manually | *(reserved — no current example)* | none |

### The importer contract

There is exactly **one mandatory rule**, because it's the only thing every
destination shares:

> **Never delete, never destroy.** An importer may create and (where the app
> supports it) update transactions in place. It must **never** delete a
> transaction, empty a trash, or otherwise remove user data — even auto-created
> "phantom" rows, even when re-syncing. If a clean-up seems necessary, surface it
> to the user and let them decide.

Everything else is **per-app, not required by the contract**. The Finerd importer
happens to do structural dedupe, verified-balance reconciliation, and an
earn→income / redeem→expense mapping — but those exist because the Finerd MCP
exposes those concepts. Another app's MCP may not. Treat
[`skills/finerd-import/SKILL.md`](../skills/finerd-import/SKILL.md) as a **reference
implementation to adapt**, not a spec to copy. Implement only what your app's MCP
actually supports; keep the never-delete rule regardless.

Start a new importer from `templates/import-skill/`.

## The boundary — the unified CSV

Three columns, newest-first, signed integer amounts (`earn +`, `redeem −`):

```
Date,Description,Amount
2026-03-15,Aspire Card Bonus,2982
2026-02-24,"SFO-CDG-BCN, award ticket",-60000
```

Filename `<program>_activity_<from>_<to>.csv` uses the **actual covered range**, never
the requested one, so it never overstates coverage. Alongside it, extractors print
`BALANCE:/COVERED:/REQUESTED:/FILE:/ROWS:` for the orchestrator (and importers) to
parse. This shape is defined once and consumed by both sides — see the "Unified
output contract" in [CLAUDE.md](../CLAUDE.md) and [CONTRIBUTING.md](../CONTRIBUTING.md).
**Do not diverge from it**; that's what keeps extractors and importers decoupled.

## Shared helpers (copied verbatim, CI-enforced)

Skills ship self-contained, so two contract helpers are physically duplicated into
every skill that needs them and CI byte-diffs all copies against the canonical pair
under `skills/points-activity/scripts/`:

- `activity_output.py` — **write** side, used by extractors.
- `canonical_csv.py` — **read** side, used by importers.

Change the canonical copy and run the sync; CI fails if any copy drifts.
