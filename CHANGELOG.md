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

### Notes
- Bumped `plugin.json` to **0.3.0** for the breaking earning-date change.
- The importer layer (Finerd/Monarch/Copilot via their MCPs) lands in a later
  phase; this release is still extract-to-CSV only.

## [0.2.1] and earlier
See git history prior to the introduction of this CHANGELOG.
