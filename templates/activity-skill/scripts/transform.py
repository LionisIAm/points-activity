#!/usr/bin/env python3
"""
TEMPLATE transform -> unified contract (Date, Description, Amount) via activity_output.

This template is runnable as-is against tests/fixtures/raw_dump.txt (a fake
"Example Rewards" program) so you can see the whole pipeline work before adapting.

Input raw file: '~~'-delimited lines (console-dump lines, prefix stripped). For the
example program the fields are:
    YYYY-MM-DD ~~ Kind ~~ Description ~~ Amount
where Kind is 'E' (earn) or 'R' (redeem) and Amount is a signed integer.

YOUR JOB when adapting:
  - parse your program's real dump format,
  - classify each row as 'earn' or 'redeem' (the source-data signal: a category
    field, status text, the sign of the amount, an award marker, etc.),
  - keep only the SPENDABLE currency (ignore status/qualifying points),
  - emit 4-tuples (date_iso, description, amount_int, kind).
The shared activity_output.py does ALL grouping (earn -> collapse by (date,
description); redeem -> one row each) and drops zero rows. Do NOT collapse here.

Usage: python3 transform.py raw.txt out_dir [from] [to] [balance]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from activity_output import write_activity, filter_by_period

PROGRAM = 'example'   # TODO: your program slug; matches <program>_activity_*.csv


def amount(s):
    s = s.replace(',', '').strip()
    try:
        return int(s)
    except Exception:
        return 0


def main():
    raw, out_dir = sys.argv[1], sys.argv[2]
    rfrom = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != '-' else None
    rto = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != '-' else None
    bal = sys.argv[5] if len(sys.argv) > 5 else None

    rows = [l.split('~~') for l in open(raw).read().strip().split('\n') if l.strip()]
    out = []
    for parts in rows:
        if len(parts) < 4:
            continue
        date = parts[0].strip()
        kind_code = parts[1].strip()
        desc = parts[2].strip()
        amt = amount(parts[3])
        kind = 'redeem' if kind_code == 'R' else 'earn'   # TODO: your classifier
        out.append((date, desc, amt, kind))

    out = filter_by_period(out, rfrom, rto)
    write_activity(PROGRAM, out, out_dir, rfrom, rto, bal)


if __name__ == '__main__':
    main()
