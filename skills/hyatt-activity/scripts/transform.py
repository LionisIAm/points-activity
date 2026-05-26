#!/usr/bin/env python3
"""
Hyatt transform -> unified contract (Date, Description, Amount) via activity_output.

Input raw file: '~'-delimited lines (HX console lines, prefix stripped):
    date~category~pointsType~baseAmount~totalAmount~qualifyingNights~name~bonusDetail
(date ISO; bonusDetail = "Label=amount; Label=amount" or empty)

Logic (verified to reconcile to balance):
  - Explode each point-bearing component into its own row:
      STAY: baseAmount (if >0) as "Base Points/Miles" + each bonusDetail item.
      else (BONUS/AWARD/PARTNER_EARN): amount in totalAmount; + any bonusDetail items.
  - A component counts (PointsType P) when txn pointsType=='P', or it's a STAY/bonus
    component, or AWARD/PARTNER_EARN with nonzero total. 'N' (nights) excluded.
  - Redemptions (AWARD) keep real date; everything else -> end of month; collapse by
    (date, component); drop zeros.

Usage: python3 transform.py raw.txt out_dir [requested_from] [requested_to] [balance]
"""
import calendar, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# activity_output.py is shipped in points-activity/scripts; sub-skills get a copy at deploy.
from activity_output import write_activity, filter_by_period

def eom(d):
    y, m, _ = d.split('-'); y, m = int(y), int(m)
    return f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"

def main():
    raw, out_dir = sys.argv[1], sys.argv[2]
    rfrom = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != '-' else None
    rto   = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != '-' else None
    bal   = sys.argv[5] if len(sys.argv) > 5 else None

    rows = [l.split('~') for l in open(raw).read().strip().split('\n') if l.strip()]
    out = []
    for date, cat, ptype, base, total, qn, name, bonus in rows:
        base, total = int(base), int(total)
        bonus_items = []
        if bonus.strip():
            for part in bonus.split(';'):
                k, v = part.rsplit('=', 1); bonus_items.append((k.strip(), int(v)))
        comps = []
        if cat == 'STAY':
            if base > 0: comps.append(('Base Points/Miles', base, ptype))
            for k, v in bonus_items: comps.append((k, v, 'P'))
        else:
            pt = 'P' if (ptype == 'P' or (cat in ('PARTNER_EARN', 'AWARD') and total != 0)) else ptype
            if total != 0: comps.append((name, total, pt))
            for k, v in bonus_items: comps.append((k, v, 'P'))
        if not comps:
            comps.append((name, 0, ptype))
        for label, pts, pt in comps:
            if pt != 'P':
                continue
            d = date if cat == 'AWARD' else eom(date)
            out.append((d, label, pts))

    agg = {}
    for d, desc, a in out:
        agg[(d, desc)] = agg.get((d, desc), 0) + a
    collapsed = [(d, desc, a) for (d, desc), a in agg.items()]
    collapsed = filter_by_period(collapsed, rfrom, rto)
    write_activity('hyatt', collapsed, out_dir, rfrom, rto, bal)

if __name__ == '__main__':
    main()
