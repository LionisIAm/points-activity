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

### Notes
- No behavior change in this groundwork. The output-contract migration
  (per-date grouping, 4-tuple earn/redeem classification) and the importer layer
  land in subsequent phases and will bump the MAJOR-ish version with explicit
  migration notes here.

## [0.2.1] and earlier
See git history prior to the introduction of this CHANGELOG.
