#!/usr/bin/env python3
"""
Accor transform -> unified contract (Date, Description, Amount) via activity_output.

Input raw file: '~~'-delimited lines (AC console lines, prefix stripped):
    year ~~ description ~~ DATE ~~ reward ~~ status ~~ nights
Date format depends on the user's Accor locale: US shows MM/DD/YYYY, most other
regions show DD/MM/YYYY. iso() auto-detects: if the first part > 12, it must
be DD/MM/YYYY; otherwise prefer the year-2026/2025 cross-check to disambiguate.
Only REWARD points used (status/nights ignored). Cells: "+ 626" / "- 28,000" / "-".

Logic: classify each row as 'redeem' (description starts "Stay paid with points:")
or 'earn' (everything else — stays, Platinum bonus, partner earns like Flying
Blue / Europcar / BILT). Emit 4-tuples; shared code collapses earnings by
(date, desc) and keeps redemptions per-row. Reward sum reconciles to balance
for a full-history account.

Usage: python3 transform.py raw.txt out_dir [from] [to] [balance]
"""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from activity_output import write_activity, filter_by_period

REDEEM=re.compile(r'^Stay paid with points:', re.I)
def iso(d):
    # Accor delivers dates in either MM/DD/YYYY (US locale) or DD/MM/YYYY (most
    # other locales). Detect: if the first part > 12, it's DD/MM/YYYY.
    a, b, y = d.split('/')
    a, b, y = int(a), int(b), int(y)
    if a > 12:                       # unambiguously DD/MM/YYYY
        return f"{y:04d}-{b:02d}-{a:02d}"
    if b > 12:                       # unambiguously MM/DD/YYYY
        return f"{y:04d}-{a:02d}-{b:02d}"
    # Both ≤ 12: ambiguous. Default to DD/MM/YYYY (matches the user's locale set
    # at deploy time; revisit if US users complain).
    return f"{y:04d}-{b:02d}-{a:02d}"
def rp(s):
    s=s.replace(',','').replace(' ','').strip()
    return 0 if s in ('','-') else int(s)

def main():
    raw,out_dir=sys.argv[1],sys.argv[2]
    rfrom=sys.argv[3] if len(sys.argv)>3 and sys.argv[3]!='-' else None
    rto=sys.argv[4] if len(sys.argv)>4 and sys.argv[4]!='-' else None
    bal=sys.argv[5] if len(sys.argv)>5 else None
    rows=[l.split('~~') for l in open(raw).read().strip().split('\n') if l.strip()]
    out=[]
    for parts in rows:
        yr,desc,date,reward=parts[0].strip(),parts[1].strip(),parts[2].strip(),parts[3].strip()
        p=rp(reward)
        kind='redeem' if REDEEM.match(desc) else 'earn'
        out.append((iso(date), desc, p, kind))
    out=filter_by_period(out, rfrom, rto)
    write_activity('accor', out, out_dir, rfrom, rto, bal)

if __name__=='__main__': main()
