#!/usr/bin/env python3
"""
Registration checks — guards the single most common contributor bug:
"I added a program but the orchestrator doesn't see it."

Pure stdlib, no deps. Run from anywhere:
    python3 tests/test_registration.py

What it enforces (hard — non-zero exit on failure):
  1. Every skill dir under skills/ has a SKILL.md.
  2. SKILL.md frontmatter `name:` equals the directory name.
  3. Every `*-activity` extractor (except the orchestrator) is referenced in the
     orchestrator routing table (skills/points-activity/SKILL.md).

Soft (warn only, never fails CI) — tightened in later phases:
  - README "Supported programs" presence (README uses display names, not skill
    dir names, so a verbatim check would false-positive until a name map exists).
  - per-program tests/ and trigger-eval presence (backfilled in the v0.3 work).
"""
import os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, 'skills')
ORCH_MD = os.path.join(SKILLS, 'points-activity', 'SKILL.md')

ORCHESTRATOR = 'points-activity'   # the router itself — not a program extractor


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def skill_dirs():
    out = []
    for p in sorted(glob.glob(os.path.join(SKILLS, '*'))):
        name = os.path.basename(p)
        if not os.path.isdir(p):
            continue
        if name.startswith('_'):       # scaffolds, if any ever live under skills/
            continue
        out.append(name)
    return out


def frontmatter_name(md):
    # frontmatter is the first --- ... --- block
    m = re.match(r'^---\s*\n(.*?)\n---', md, re.S)
    block = m.group(1) if m else md
    nm = re.search(r'^name:\s*(.+?)\s*$', block, re.M)
    return nm.group(1).strip() if nm else None


def main():
    errors, warnings = [], []
    orch = read(ORCH_MD)

    names = skill_dirs()
    for name in names:
        skill_md = os.path.join(SKILLS, name, 'SKILL.md')
        if not os.path.exists(skill_md):
            errors.append(f'{name}: missing SKILL.md')
            continue
        md = read(skill_md)

        fm = frontmatter_name(md)
        if fm != name:
            errors.append(f'{name}: frontmatter name {fm!r} != dir name {name!r}')

        # Program extractors must be routed by the orchestrator.
        if name.endswith('-activity') and name != ORCHESTRATOR:
            # match the skill name in backticks in the routing table, or bare
            if f'`{name}`' not in orch and name not in orch:
                errors.append(
                    f'{name}: not referenced in orchestrator routing table '
                    f'(skills/points-activity/SKILL.md)')

    if warnings:
        print('WARNINGS:')
        for w in warnings:
            print('  -', w)
    if errors:
        print('FAILED:')
        for e in errors:
            print('  -', e)
        sys.exit(1)
    print(f'registration OK: {len(names)} skill(s) checked')


if __name__ == '__main__':
    main()
