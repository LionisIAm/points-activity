# Changelog

All notable changes to this project are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); versioning follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

Groundwork toward **v0.3.0** — a two-role architecture (program **extractors**
that produce a CSV, optional **importers** that push that CSV into a finance app
via its MCP) plus a per-date output contract. Landing in phases so each is
independently reviewable.

### Added
- **CI** (`.github/workflows/ci.yml`): Python syntax check (stdlib-only enforced
  via `py_compile`), per-program unit tests, registration checks, and JS syntax
  check (`node --check`). Previously the repo claimed CI ran tests but shipped
  only a release workflow.
- **`tests/test_registration.py`**: fails the build if a `*-activity` extractor is
  missing from the orchestrator routing table, or if a skill's frontmatter `name`
  doesn't match its directory. Turns the "update ALL these files" prose checklist
  into an enforced invariant.
- This CHANGELOG.

### Changed (BREAKING — output contract)
- **Earnings now group by their REAL transaction date**, not the last day of the
  month. A stay or card-credit dated `2026-03-15` stays on `2026-03-15`. Previously
  earnings were collapsed to month-end (`2026-03-31`). Redemptions already kept their
  real date; that is unchanged. CSV columns (`Date, Description, Amount`) are
  unchanged — only the dates of earning rows move. Anything that keyed off month-end
  earning dates must adjust.
- **Classification moved into the shared helper.** Each `transform.py` now emits
  4-tuples `(date, description, amount, kind)` with `kind in {'earn','redeem'}`;
  `activity_output.py:write_activity()` owns the grouping (earn → collapse by
  (date, description); redeem → each its own row). Adding a program is now
  parse-and-classify only — no per-program collapse logic. 3-tuples are still
  accepted (treated as `earn`) for back-compat.

### Added
- CI step asserting every `activity_output.py` copy is byte-identical to the
  canonical `skills/points-activity/scripts/activity_output.py` — the
  "change all copies in lockstep" rule is now enforced, not just documented.
- `templates/activity-skill/`: a runnable contributor scaffold (fake "Example
  Rewards" program) with `wait_for_login.js`, both extractor paths, `transform.py`,
  the canonical `activity_output.py`, and a passing test. CONTRIBUTING now says
  "copy the template"; CI runs the template's test too so the scaffold can't rot.
- `wait_for_login.js` added to all 7 existing extractors; the orchestrator login
  step is standardized on polling (no manual "are you logged in?" prompt).
- **Importer layer** (pluggable "sinks"). `docs/ARCHITECTURE.md` defines two roles —
  extractors (`*-activity`, program → CSV) and importers (`*-import`, CSV → finance
  app). The only mandatory importer rule is **never-delete**; everything else
  (dedupe, verified-balance, earn→income mapping) is per-app, with `finerd-import` as
  the reference. Shared reader `canonical_csv.py` mirrors `activity_output.py` and is
  CI byte-diffed too.
- `skills/finerd-import/` — the former `points-import`, renamed and reframed as the
  reference api/mcp importer (no behavior change to the Finerd flow).
- `skills/monarch-import/`, `skills/copilot-import/` — scaffolds (api/mcp via each
  app's MCP); pipeline shape fixed, app-specific MCP calls marked TODO.
- `templates/import-skill/` — scaffold for new importers; CONTRIBUTING/README/CLAUDE
  reframed so extractors stay app-agnostic and importers are opt-in.
- **Three new program extractors**, app-agnostic (CSV-only), dogfooding the new
  template + structure: `flyingblue-activity` (Air France-KLM, internal JSON API),
  `qatar-activity` (Privilege Club / Avios, DOM scrape), `hilton-activity` (Hilton
  Honors, paginated DOM scrape — note: redemptions aren't on Hilton's web feed). Each
  ships sanitized fixtures + unit tests and is registered in the routing table and
  README. Hilton removed from the generic-playbook list.

### Notes
- Bumped `plugin.json` to **0.3.0** for the breaking earning-date change.
- The importer layer (Finerd/Monarch/Copilot via their MCPs) lands in a later
  phase; this release is still extract-to-CSV only.

## [0.2.1] and earlier
See git history prior to the introduction of this CHANGELOG.
