#!/usr/bin/env python3
"""
United transform -> unified contract (Date, Description, Amount) via activity_output.

Input raw file: '~~'-delimited lines (UA console lines, prefix stripped):
    YYYY-MM-DD ~~ ActivityType ~~ Description ~~ TotalMiles ~~ IsRedeposit
Only MILES (TotalMiles) used; PQP/PQF/PQS ignored.

Logic: 'F' = flight -> keep real date, own row; else earning/transfer -> end of month;
collapse by (date, desc); drop zeros. Miles sum reconciles to balance for full history.

Usage: python3 transform.py raw.txt out_dir [from] [to] [balance]
"""
import calendar, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from activity_output import write_activity, filter_by_period

def eom(d): y,m,dd=d.split('-'); y,m=int(y),int(m); return f"{y:04d}-{m:02d}-{calendar.monthrange(y,m)[1]:02d}"
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
    agg={}
    for parts in rows:
        date,atype,desc,m=parts[0].strip(),parts[1].strip(),parts[2].strip(),parts[3].strip()
        v=miles(m)
        key=(date,desc) if atype=='F' else (eom(date),desc)
        agg[key]=agg.get(key,0)+v
    collapsed=[(d,desc,a) for (d,desc),a in agg.items()]
    collapsed=filter_by_period(collapsed,rfrom,rto)
    write_activity('united', collapsed, out_dir, rfrom, rto, bal)

if __name__=='__main__': main()
