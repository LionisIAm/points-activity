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
  - REDEMPTION  = any entry with tp < 0. These are transfers to partners (World of
    Hyatt, British Airways, Accor, Atmos, Flying Blue, ...) and reversals/refunds.
    Keep the REAL date; each entry is its OWN row and is NEVER merged — two identical
    -9,000 World of Hyatt transfers on the same day stay as two separate rows so each
    maps to a distinct partner transfer / booking.
    Description = the title (merchant/partner), e.g. "World of Hyatt".
  - EARNING     = tp >= 0. Explode into its benefit ITEMS and move each to the LAST DAY
    of its month, collapsing by (month, benefit-item-title) summed across ALL merchants
    (no merchant in the key — per requirement). E.g. every "3x Points on Dining" in a
    month becomes one row.

Drop zero-amount rows after collapsing. Reconciles: sum(Amount) == current balance
(Bilt shows full history; verified 80,723 == 80.7k balance).

NOTE on extraction: the API is GET https://api.biltrewards.com/loyalty/activity
?month=M&year=Y with an `authorization: Bearer <jwt>` header (jwt in localStorage).
Only month+year filter; no range/limit. Iterate months backward until empty.

Usage: python3 transform.py raw.json out_dir [from] [to] [balance]
"""
import calendar, json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from activity_output import write_activity, filter_by_period

def eom(d):
    y, m, _ = d.split('-'); y, m = int(y), int(m)
    return f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"

def main():
    raw, out_dir = sys.argv[1], sys.argv[2]
    rfrom = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != '-' else None
    rto   = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != '-' else None
    bal   = sys.argv[5] if len(sys.argv) > 5 else None

    entries = json.load(open(raw))
    redemptions = []   # one row per negative entry — NOT collapsed (each transfer/reversal distinct)
    earn_agg = {}      # earnings collapsed by (month, benefit-item-title), no merchant
    for i, e in enumerate(entries):
        d = e['d']; tp = int(e.get('tp', 0) or 0)
        if not d:
            continue
        if tp < 0:
            # redemption / reversal: real date, its OWN row, never merged (even if same
            # date+title as another — e.g. two -9,000 World of Hyatt transfers stay as two
            # rows so each maps to a distinct partner transfer / booking).
            redemptions.append((d, e.get('t', '').strip(), tp))
        else:
            # earning: explode benefit items, month-end, collapse by (month, item title) — no merchant
            for bn in (e.get('b') or []):
                v = bn.get('v')
                if not v:
                    continue
                key = (eom(d), bn['t'].strip())
                earn_agg[key] = earn_agg.get(key, 0) + int(v)

    rows = redemptions + [(d, desc, a) for (d, desc), a in earn_agg.items()]
    rows = filter_by_period(rows, rfrom, rto)
    write_activity('bilt', rows, out_dir, rfrom, rto, bal)

if __name__ == '__main__':
    main()
