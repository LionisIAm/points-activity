#!/usr/bin/env python3
"""
Hilton Honors transform -> unified contract (Date, Description, Amount)
via activity_output.

Input raw file: '~~'-delimited lines (HH console lines, prefix stripped):
    YYYY-MM-DD ~~ Kind ~~ Description ~~ Confirmation ~~ Points

Kind is 'earn' or 'refund'. Points is unsigned positive (Hilton's display
is positive for both kinds). All rows here are positive credits to the
account — redemptions (debits) are NOT exposed on the web activity feed (a
known Hilton web glitch), so the CSV reflects earnings + refunds only.

Classification: every input row is `kind='earn'` for the shared collapser,
which sums same-(date, description) lines. The "refund" tag is preserved
in the description prefix only (so refunds stay distinguishable from fresh
earnings downstream).

Usage: python3 transform.py raw.txt out_dir [from] [to] [balance]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from activity_output import write_activity, filter_by_period


def parse_points(s):
    s = s.replace(',', '').replace('+', '').strip()
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
        if len(parts) < 5:
            continue
        date = parts[0].strip()
        kind_tag = parts[1].strip().lower()
        desc = parts[2].strip()
        # confirmation = parts[3].strip()
        pts = parse_points(parts[4])
        if pts == 0:
            continue
        # Both 'earn' and 'refund' are positive credits. Use 'earn' for the
        # shared collapser (it groups by date+desc). The desc already encodes
        # 'Refund - <hotel>' for refunds (set in scrape_activity.js).
        out.append((date, desc, pts, 'earn'))

    out = filter_by_period(out, rfrom, rto)
    write_activity('hilton', out, out_dir, rfrom, rto, bal)


if __name__ == '__main__':
    main()
