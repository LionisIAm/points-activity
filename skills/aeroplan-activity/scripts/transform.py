#!/usr/bin/env python3
"""
Aeroplan transform -> unified contract (Date, Description, Amount) via activity_output.

Input raw file: '|'-delimited lines (AE console lines, prefix stripped):
    MONTH|DD|YYYY|Partner|Description|±N Pts

Logic: redemption (Flight Reward Booking / its Cancellation / Family Sharing
redemption) keeps real date; else earning/transfer -> end of month; collapse by
(date, "Partner: Description"); drop zeros. Balance NOT reconciled (Family Sharing:
this account's activity is incomplete for the pooled balance).

Usage: python3 transform.py raw.txt out_dir [from] [to] [balance]
"""
import calendar, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from activity_output import write_activity, filter_by_period

MON={'JAN':1,'FEB':2,'MAR':3,'APR':4,'MAY':5,'JUN':6,'JUL':7,'AUG':8,'SEP':9,'OCT':10,'NOV':11,'DEC':12}
REDEEM=re.compile(r'Flight Reward Booking|Cancellation - Flight Reward|Family Sharing redemption', re.I)
def iso(mon,d,y): return f"{int(y):04d}-{MON[mon.upper()]:02d}-{int(d):02d}"
def eom(mon,y): m=MON[mon.upper()]; return f"{int(y):04d}-{m:02d}-{calendar.monthrange(int(y),m)[1]:02d}"
def pts(s):
    s=s.replace('Pts','').replace(',','').replace(' ','').strip()
    return int(s) if s and s.lstrip('+-').isdigit() else 0

def main():
    raw,out_dir=sys.argv[1],sys.argv[2]
    rfrom=sys.argv[3] if len(sys.argv)>3 and sys.argv[3]!='-' else None
    rto=sys.argv[4] if len(sys.argv)>4 and sys.argv[4]!='-' else None
    bal=sys.argv[5] if len(sys.argv)>5 else None
    rows=[l.split('|') for l in open(raw).read().strip().split('\n') if l.strip()]
    agg={}
    for parts in rows:
        mon,d,y,partner,desc,amt=parts[0],parts[1],parts[2],parts[3],parts[4],parts[5]
        p=pts(amt); full=f"{partner.strip()}: {desc.strip()}"
        key=(iso(mon,d,y),full) if REDEEM.search(desc) else (eom(mon,y),full)
        agg[key]=agg.get(key,0)+p
    collapsed=[(d,desc,a) for (d,desc),a in agg.items()]
    collapsed=filter_by_period(collapsed,rfrom,rto)
    write_activity('aeroplan', collapsed, out_dir, rfrom, rto, bal)

if __name__=='__main__': main()
