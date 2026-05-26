#!/usr/bin/env python3
"""
Accor transform -> unified contract (Date, Description, Amount) via activity_output.

Input raw file: '~~'-delimited lines (AC console lines, prefix stripped):
    year ~~ description ~~ MM/DD/YYYY ~~ reward ~~ status ~~ nights
Only REWARD points used (status/nights ignored). Cells: "+ 626" / "- 28,000" / "-".

Logic: redemption ("Stay paid with points: ...") keeps real date; else -> end of
month; collapse by (date, desc); drop zeros. Reward sum reconciles to balance for a
full-history account.

Usage: python3 transform.py raw.txt out_dir [from] [to] [balance]
"""
import calendar, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from activity_output import write_activity, filter_by_period

REDEEM=re.compile(r'^Stay paid with points:', re.I)
def eom(d): m,dd,y=d.split('/'); m,y=int(m),int(y); return f"{y:04d}-{m:02d}-{calendar.monthrange(y,m)[1]:02d}"
def iso(d): m,dd,y=d.split('/'); return f"{int(y):04d}-{int(m):02d}-{int(dd):02d}"
def rp(s):
    s=s.replace(',','').replace(' ','').strip()
    return 0 if s in ('','-') else int(s)

def main():
    raw,out_dir=sys.argv[1],sys.argv[2]
    rfrom=sys.argv[3] if len(sys.argv)>3 and sys.argv[3]!='-' else None
    rto=sys.argv[4] if len(sys.argv)>4 and sys.argv[4]!='-' else None
    bal=sys.argv[5] if len(sys.argv)>5 else None
    rows=[l.split('~~') for l in open(raw).read().strip().split('\n') if l.strip()]
    agg={}
    for parts in rows:
        yr,desc,date,reward=parts[0].strip(),parts[1].strip(),parts[2].strip(),parts[3].strip()
        p=rp(reward)
        key=(iso(date),desc) if REDEEM.match(desc) else (eom(date),desc)
        agg[key]=agg.get(key,0)+p
    collapsed=[(d,desc,a) for (d,desc),a in agg.items()]
    collapsed=filter_by_period(collapsed,rfrom,rto)
    write_activity('accor', collapsed, out_dir, rfrom, rto, bal)

if __name__=='__main__': main()
