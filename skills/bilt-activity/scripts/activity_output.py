#!/usr/bin/env python3
"""
Shared output contract for all points-activity sub-skills.

Every program's transform produces the SAME unified shape via write_activity():
  - CSV columns: Date, Description, Amount   (no Program column, no Unit column —
    program is in the filename; points vs miles never mix in one file)
  - Filename: <program>_activity_<from>_<to>.csv  where <from>/<to> are the ACTUAL
    covered range (oldest..newest transaction dates in the output), ISO yyyy-mm-dd.
    The covered range — never the requested range — so the name never overstates
    coverage.
  - The current balance and coverage are printed to stdout as machine-readable lines
    the orchestrator parses:
        BALANCE: <int or "unknown">
        COVERED: <from>..<to>
        REQUESTED: <from>..<to>        (echoes what was asked; "all" if unbounded)
        FILE: <path>
        ROWS: <n>

Sub-skill transforms call:
    write_activity(program, rows, out_dir, requested_from=None, requested_to=None,
                   balance=None)
where rows is a list of (date_iso, description, amount_int) already collapsed/cleaned
by the program-specific logic. Rows with amount 0 should already be dropped by the
caller; we drop them defensively too.
"""
import csv, os


def write_activity(program, rows, out_dir,
                   requested_from=None, requested_to=None, balance=None):
    out_dir = out_dir.rstrip('/')
    os.makedirs(out_dir, exist_ok=True)

    # defensive: drop zero rows, sort newest-first
    rows = [(d, desc, int(a)) for (d, desc, a) in rows if int(a) != 0]
    rows.sort(key=lambda r: (r[0], r[1]), reverse=True)

    if rows:
        dates = [r[0] for r in rows]
        covered_from, covered_to = min(dates), max(dates)
    else:
        covered_from = covered_to = (requested_to or 'none')

    fname = f"{program}_activity_{covered_from}_{covered_to}.csv"
    path = f"{out_dir}/{fname}"
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Date', 'Description', 'Amount'])
        for d, desc, a in rows:
            w.writerow([d, desc, a])

    req = 'all' if (requested_from is None and requested_to is None) \
        else f"{requested_from or 'all'}..{requested_to or 'all'}"
    print(f"BALANCE: {balance if balance is not None else 'unknown'}")
    print(f"COVERED: {covered_from}..{covered_to}")
    print(f"REQUESTED: {req}")
    print(f"FILE: {path}")
    print(f"ROWS: {len(rows)}")
    return path


def filter_by_period(rows, requested_from=None, requested_to=None):
    """Optional helper: keep rows whose ISO date is within [from, to] (inclusive).
    rows: list of (date_iso, description, amount). Either bound may be None."""
    def keep(d):
        if requested_from and d < requested_from:
            return False
        if requested_to and d > requested_to:
            return False
        return True
    return [r for r in rows if keep(r[0])]
