<!-- Quick PR. For new program submissions, please follow CONTRIBUTING.md. -->

## What this changes

<!-- One-paragraph summary -->

## Type
- [ ] New program (new sub-skill under `skills/`)
- [ ] Fix for a broken existing program
- [ ] Orchestrator / shared infrastructure change
- [ ] Documentation
- [ ] Other:

## For new programs / playbook fixes
- [ ] SKILL.md description triggers on program name + synonyms
- [ ] Trigger evals include positive cases AND near-miss negatives
- [ ] `activity_output.py` is unchanged (verbatim from another sub-skill)
- [ ] `transform.py` is stdlib-only Python (no external deps)
- [ ] No hardcoded credentials, account IDs, or PII in code or test fixtures
- [ ] Tested end-to-end on a real account; output CSV reconciles to balance (or COVERED honestly reports if the program only shows a window)
- [ ] Routing table in `skills/points-activity/SKILL.md` updated

## Sample output (sanitized)

```
<paste a few CSV rows + BALANCE/COVERED/FILE lines>
```

## Notes for reviewers

<!-- Anything that needs extra eyeballs (e.g. new XHR hooks, new auth-capture pattern) -->
