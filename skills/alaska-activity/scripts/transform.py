#!/usr/bin/env python3
"""
Alaska Atmos Rewards transform -> unified contract (Date, Description, Amount).

Input raw file: '~'-delimited lines (AK console lines, prefix stripped):
    MM/DD/YYYY~Activity~Status~Points~BonusPoints~TotalPoints~StatusPoints

Only TOTAL POINTS (col 6, index 5) is the spendable currency. STATUS POINTS (col 7) is
the elite-qualifying currency and is IGNORED (like United PQP / Accor status points).

CLASSIFICATION — deliberately NOT a status whitelist. We capture every row (the scraper
uses a structural date+number filter), and decide redemption-vs-earning by robust signals
so unanticipated status labels still route correctly:

  redemption-type (keep REAL date, each row separate, matched to itineraries later) iff:
    - Total points is negative (any spend), OR
    - the Activity text carries an award/booking marker: a flight route like "BCN-SFO",
      a "Rollback:" reversal, or the words Reward/Award/Redemption/Redeposit.
  everything else = earning/transfer -> move to last day of month, collapse identical
  (date, description) by summing.

This means a change/rebook nets out naturally and per-leg: e.g. 4x -70,000 Redeemed +
2x +70,000 "Rollback: ... Redeposited" = -140,000 for the trip, each row preserved.

After collapsing, drop zero-Total rows (status-only award rows and monthly status-point
accruals contribute 0 to spendable balance).

CAUTION — case-duplicate descriptions: Atmos sometimes lists the same award row twice
with the passenger name in different case. Those are REAL separate transactions (verified
against the visible table), so we do NOT case-normalize/merge them.

Balance is NOT reconciled: Atmos shows max 24 months, so older accruals fall outside the
window (the observed gap equalled the pre-window starting balance).

Usage: python3 transform.py raw.txt out_dir [from] [to] [balance]
"""
import calendar, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from activity_output import write_activity, filter_by_period

# award/booking markers in the Activity text (case-insensitive)
AWARD_MARKER = re.compile(r'\b[A-Z]{3}-[A-Z]{3}\b|rollback|reward|award|redemption|redeposit', re.I)

def eom(d):
    m, dd, y = d.split('/'); m, y = int(m), int(y)
    return f"{y:04d}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"

def iso(d):
    m, dd, y = d.split('/'); return f"{int(y):04d}-{int(m):02d}-{int(dd):02d}"

def num(s):
    s = s.replace(',', '').strip()
    return int(s) if s and s.lstrip('-').isdigit() else 0

def is_redemption(activity, total):
    return total < 0 or bool(AWARD_MARKER.search(activity))

def main():
    raw, out_dir = sys.argv[1], sys.argv[2]
    rfrom = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != '-' else None
    rto   = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != '-' else None
    bal   = sys.argv[5] if len(sys.argv) > 5 else None

    rows = [l.split('~') for l in open(raw).read().strip().split('\n') if l.strip()]
    agg = {}
    for c in rows:
        date, activity = c[0], c[1].strip()
        total = num(c[5])
        if is_redemption(activity, total):
            key = (iso(date), activity)          # real date, keep each row separate
        else:
            key = (eom(date), activity)          # earning/transfer -> end of month
        agg[key] = agg.get(key, 0) + total

    collapsed = [(d, desc, a) for (d, desc), a in agg.items()]
    collapsed = filter_by_period(collapsed, rfrom, rto)
    write_activity('alaska', collapsed, out_dir, rfrom, rto, bal)

if __name__ == '__main__':
    main()
