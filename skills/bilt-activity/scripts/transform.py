#!/usr/bin/env python3
"""
Bilt Rewards transform -> unified contract (Date, Description, Amount).

Bilt is a bank/card program: earnings are per-purchase (hundreds/thousands of rows),
redemptions are point transfers out to airline/hotel partners. We collapse heavily.

Input: a JSON array (from the API, via dump) of entries shaped:
    {"d":"YYYY-MM-DD","t":<merchant/title>,"a":<activity>,"s":<pointState>,
     "tp":<totalPoints int>,"b":[{"t":<benefit item title>,"v":<points int>}, ...]}
Only point-bearing benefit items are included in `b` (cash-back "Earn Bilt Cash" and
non-point benefits like status/credit are already stripped upstream; defensively we
also ignore any b-item whose v is null/0). `tp` (totalPoints) == sum of b[].v (verified).

Classification — purely by SIGN, not status text (robust to vocabulary):
  - kind='redeem' = any entry with tp < 0. Transfers to partners (World of Hyatt,
    British Airways, Accor, Atmos, Flying Blue, ...) and reversals/refunds. One
    row per source entry; shared code keeps redemptions separate (two identical
    -9,000 World of Hyatt transfers on the same day stay as TWO rows, each
    mapping to a distinct partner transfer / booking). Description = the title.
  - kind='earn'   = tp >= 0. Explode into benefit ITEMS, emit each as its own
    4-tuple with the benefit-item title as description (no merchant — per
    requirement). Shared code collapses by (date, item-title) summed, so every
    "3x Points on Dining" on the same date becomes one row.

Shared code drops zero-amount rows. Reconciles: sum(Amount) == current balance
(Bilt shows full history; verified 80,723 == 80.7k balance).

NOTE on extraction: the API is GET https://api.biltrewards.com/loyalty/activity
?month=M&year=Y with an `authorization: Bearer <jwt>` header (jwt in localStorage).
Only month+year filter; no range/limit. Iterate months backward until empty.

Usage: python3 transform.py raw.json out_dir [from] [to] [balance]
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from activity_output import write_activity, filter_by_period

def main():
    raw, out_dir = sys.argv[1], sys.argv[2]
    rfrom = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != '-' else None
    rto   = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != '-' else None
    bal   = sys.argv[5] if len(sys.argv) > 5 else None

    entries = json.load(open(raw))
    out = []
    for e in entries:
        d = e['d']; tp = int(e.get('tp', 0) or 0)
        if not d:
            continue
        if tp < 0:
            out.append((d, e.get('t', '').strip(), tp, 'redeem'))
        else:
            for bn in (e.get('b') or []):
                v = bn.get('v')
                if not v:
                    continue
                out.append((d, bn['t'].strip(), int(v), 'earn'))

    out = filter_by_period(out, rfrom, rto)
    write_activity('bilt', out, out_dir, rfrom, rto, bal)

if __name__ == '__main__':
    main()
