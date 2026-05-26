#!/usr/bin/env python3
"""
IHG transform -> unified contract (Date, Description, Amount) via activity_output.

Input raw file: '~~'-delimited lines (IX console lines, prefix stripped):
    MM/DD/YYYY ~~ Description ~~ Points   (Points may have commas / '-' / ' pts')

Logic: redemption ("Redeemed points for Reward Night stay on MM/DD/YYYY ...") keeps
real date, strip per-night date so a booking's nights collapse into one Stay row;
everything else -> end of month; collapse by (date, desc); drop zeros after collapse.
Balance is NOT reconciled (IHG shows only ~365 days).

Usage: python3 transform.py raw.txt out_dir [from] [to] [balance]
"""
import calendar, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from activity_output import write_activity, filter_by_period

REDEEM = re.compile(r'^Redeemed points for Reward Night stay on \d{2}/\d{2}/\d{4}')
def eom(d): m,dd,y=d.split('/'); m,y=int(m),int(y); return f"{y:04d}-{m:02d}-{calendar.monthrange(y,m)[1]:02d}"
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
    agg={}
    for parts in rows:
        date,desc,pts=(p.strip() for p in parts)
        p=clean(pts)
        if REDEEM.match(desc):
            key=(iso(date), re.sub(r' on \d{2}/\d{2}/\d{4}','',desc))
        else:
            key=(eom(date), desc)
        agg[key]=agg.get(key,0)+p
    collapsed=[(d,desc,a) for (d,desc),a in agg.items()]
    collapsed=filter_by_period(collapsed,rfrom,rto)
    write_activity('ihg', collapsed, out_dir, rfrom, rto, bal)

if __name__=='__main__': main()
