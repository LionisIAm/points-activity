#!/usr/bin/env python3
"""
Hyatt transform -> unified contract (Date, Description, Amount) via activity_output.

Input raw file: '~'-delimited lines (HX console lines, prefix stripped):
    date~category~pointsType~baseAmount~totalAmount~qualifyingNights~name~bonusDetail
(date ISO; bonusDetail = "Label=amount; Label=amount" or empty)

Logic (verified to reconcile to balance):
  - Explode each point-bearing component into its own (date, desc, amount, kind):
      STAY: baseAmount (if >0) with the HOTEL NAME as description (so the user
        sees "Hyatt Centric Faneuil Hall Boston" not generic "Base Points/Miles")
        + each bonusDetail item (description = the bonus label).
      else (BONUS/AWARD/PARTNER_EARN): amount in totalAmount; + any bonusDetail items.
  - A component counts (PointsType P) when txn pointsType=='P', or it's a STAY/bonus
    component, or AWARD/PARTNER_EARN with nonzero total. 'N' (nights) excluded.
  - kind='redeem' when the source transaction category is AWARD (so each award
    stay stays its own row); everything else (STAY/BONUS/PARTNER_EARN base +
    bonuses) is kind='earn' and gets collapsed by (date, desc) in shared code.

Usage: python3 transform.py raw.txt out_dir [requested_from] [requested_to] [balance]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# activity_output.py is shipped in points-activity/scripts; sub-skills get a copy at deploy.
from activity_output import write_activity, filter_by_period

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
            # Use the hotel name (not generic "Base Points/Miles") so the
            # description carries useful context downstream.
            if base > 0: comps.append((name or 'Base Points/Miles', base, ptype))
            for k, v in bonus_items: comps.append((k, v, 'P'))
        else:
            pt = 'P' if (ptype == 'P' or (cat in ('PARTNER_EARN', 'AWARD') and total != 0)) else ptype
            if total != 0: comps.append((name, total, pt))
            for k, v in bonus_items: comps.append((k, v, 'P'))
        if not comps:
            comps.append((name, 0, ptype))
        kind = 'redeem' if cat == 'AWARD' else 'earn'
        for label, pts, pt in comps:
            if pt != 'P':
                continue
            out.append((date, label, pts, kind))

    out = filter_by_period(out, rfrom, rto)
    write_activity('hyatt', out, out_dir, rfrom, rto, bal)

if __name__ == '__main__':
    main()
