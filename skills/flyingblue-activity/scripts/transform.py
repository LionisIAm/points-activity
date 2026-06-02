#!/usr/bin/env python3
"""
Flying Blue transform -> unified contract (Date, Description, Amount) via activity_output.

Input raw file: '~~'-delimited lines (FB console lines, prefix stripped):
    YYYY-MM-DD ~~ Kind ~~ Description ~~ Miles
Where Kind is 'E' (earn) or 'R' (redeem). Miles is signed (negative for redemptions).

XP/qualifying credits are dropped upstream in fetch_activity.js (they aren't part
of the flattened rows). Sum of Miles reconciles to summary.miles for the full
history (the only call the API exposes returns everything).

Usage: python3 transform.py raw.txt out_dir [from] [to] [balance]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from activity_output import write_activity, filter_by_period


def miles(s):
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
        date = parts[0].strip()
        kind_code = parts[1].strip()
        desc = parts[2].strip()
        m = parts[3].strip()
        v = miles(m)
        kind = 'redeem' if kind_code == 'R' else 'earn'
        out.append((date, desc, v, kind))
    out = filter_by_period(out, rfrom, rto)
    write_activity('flyingblue', out, out_dir, rfrom, rto, bal)


if __name__ == '__main__':
    main()
