#!/usr/bin/env python3
"""
IHG transform -> unified contract (Date, Description, Amount) via activity_output.

Input raw file: '~~'-delimited lines (IX console lines, prefix stripped):
    MM/DD/YYYY ~~ Description ~~ Points   (Points may have commas / '-' / ' pts')

Logic: classify each row as kind='redeem' (description starts "Redeemed points
for Reward Night stay on MM/DD/YYYY ...") or kind='earn' (everything else).
For redemptions, strip the per-night date from the description so a multi-night
booking's nights collapse into ONE row in shared code (since shared code merges
earn rows by (date, desc), but multi-night redemptions on the SAME booking date
share a normalized description — wait, redemptions don't merge in shared code,
but multi-night IHG bookings legitimately share the SAME booking date with the
SAME normalized description, and the user wants one row per booking, not per
night). So multi-night merging is done HERE, in the program-specific code:
collapse redemption rows by (date, normalized-desc) BEFORE emitting. Earnings
are emitted raw — shared code collapses them. Balance is NOT reconciled (IHG
shows only ~365 days).

Usage: python3 transform.py raw.txt out_dir [from] [to] [balance]
"""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from activity_output import write_activity, filter_by_period

REDEEM = re.compile(r'^Redeemed points for Reward Night stay on \d{2}/\d{2}/\d{4}')
def iso(d): m,dd,y=d.split('/'); return f"{int(y):04d}-{int(m):02d}-{int(dd):02d}"
def clean(s):
    s=s.replace(',','').replace('pts','').strip()
    return int(s) if s and s.lstrip('-').isdigit() else 0

def main():
    raw,out_dir=sys.argv[1],sys.argv[2]
    rfrom=sys.argv[3] if len(sys.argv)>3 and sys.argv[3]!='-' else None
    rto=sys.argv[4] if len(sys.argv)>4 and sys.argv[4]!='-' else None
    bal=sys.argv[5] if len(sys.argv)>5 else None
    rows=[l.split('~~') for l in open(raw).read().strip().split('\n') if l.strip()]
    redeem_agg={}   # multi-night IHG bookings: merge per-night rows into one
    earn_rows=[]
    for parts in rows:
        date,desc,pts=(p.strip() for p in parts)
        p=clean(pts)
        if REDEEM.match(desc):
            norm=re.sub(r' on \d{2}/\d{2}/\d{4}','',desc)
            key=(iso(date), norm)
            redeem_agg[key]=redeem_agg.get(key,0)+p
        else:
            earn_rows.append((iso(date), desc, p, 'earn'))
    out=earn_rows + [(d, desc, a, 'redeem') for (d, desc), a in redeem_agg.items()]
    out=filter_by_period(out, rfrom, rto)
    write_activity('ihg', out, out_dir, rfrom, rto, bal)

if __name__=='__main__': main()
