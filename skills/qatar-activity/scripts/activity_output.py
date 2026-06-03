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

Sub-skills produce a flat list of 4-tuples and call:
    write_activity(program, rows, out_dir, requested_from=None, requested_to=None,
                   balance=None)
where rows is a list of (date_iso, description, amount_int, kind) tuples with
kind in {'earn', 'redeem'}. The shared grouping rule is:
  - kind='earn'   → collapse by (date, description) summing. Used for monthly
                    card-spend, base points, tier bonuses, partner earns —
                    anything that's just adding points.
  - kind='redeem' → each row stays separate. Used for award redemptions,
                    partner transfers out, reversals — each represents a distinct
                    booking/transaction and may later be matched to a money
                    receipt/itinerary, so they must NOT be merged.
The 'kind' tag is NOT written to the CSV. Classification is the sub-skill's job
(it has the source-data signals — category fields, status text, sign, etc.);
grouping is centralized here so adding a new program means writing parsing +
classification only.

Three-tuple inputs (date, description, amount) are still accepted for backward
compatibility and treated as 'earn' (the common case).
"""
import csv, os


def write_activity(program, rows, out_dir,
                   requested_from=None, requested_to=None, balance=None):
    out_dir = out_dir.rstrip('/')
    os.makedirs(out_dir, exist_ok=True)

    # split by kind, drop zeros, collapse earnings
    earn_agg = {}
    redeem_rows = []
    for r in rows:
        if len(r) == 4:
            d, desc, a, kind = r
        else:
            d, desc, a = r
            kind = 'earn'
        a = int(a)
        if a == 0:
            continue
        if kind == 'redeem':
            redeem_rows.append((d, desc, a))
        elif kind == 'earn':
            key = (d, desc)
            earn_agg[key] = earn_agg.get(key, 0) + a
        else:
            raise ValueError(f"unknown kind {kind!r}; expected 'earn' or 'redeem'")
    earn_rows = [(d, desc, a) for (d, desc), a in earn_agg.items() if a != 0]
    rows = earn_rows + redeem_rows
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
    Works for 3-tuples (date, desc, amount) or 4-tuples (..., kind). Either bound
    may be None."""
    def keep(d):
        if requested_from and d < requested_from:
            return False
        if requested_to and d > requested_to:
            return False
        return True
    return [r for r in rows if keep(r[0])]
