#!/usr/bin/env python3
"""
United transform -> unified contract (Date, Description, Amount) via activity_output.

Input raw file: '~~'-delimited lines (UA console lines, prefix stripped):
    YYYY-MM-DD ~~ ActivityType ~~ Description ~~ TotalMiles ~~ IsRedeposit
Only MILES (TotalMiles) used; PQP/PQF/PQS ignored.

Logic: classify ActivityType 'F' (flight) as kind='redeem' (each its own row,
matched to itineraries later); everything else as kind='earn' (collapsed by
(date, desc) in shared code). Miles sum reconciles to balance for full history.

Usage: python3 transform.py raw.txt out_dir [from] [to] [balance]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from activity_output import write_activity, filter_by_period

def miles(s):
    s=s.replace(',','').strip()
    try: return int(s)
    except: return 0

def main():
    raw,out_dir=sys.argv[1],sys.argv[2]
    rfrom=sys.argv[3] if len(sys.argv)>3 and sys.argv[3]!='-' else None
    rto=sys.argv[4] if len(sys.argv)>4 and sys.argv[4]!='-' else None
    bal=sys.argv[5] if len(sys.argv)>5 else None
    rows=[l.split('~~') for l in open(raw).read().strip().split('\n') if l.strip()]
    out=[]
    for parts in rows:
        date,atype,desc,m=parts[0].strip(),parts[1].strip(),parts[2].strip(),parts[3].strip()
        v=miles(m)
        kind='redeem' if atype=='F' else 'earn'
        out.append((date, desc, v, kind))
    out=filter_by_period(out, rfrom, rto)
    write_activity('united', out, out_dir, rfrom, rto, bal)

if __name__=='__main__': main()
