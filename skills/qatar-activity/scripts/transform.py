#!/usr/bin/env python3
"""
Qatar Airways Privilege Club transform -> unified contract (Date, Description, Amount)
via activity_output.

Input raw file: '~~'-delimited lines (QR console lines, prefix stripped):
    YYYY-MM-DD ~~ Activity ~~ Description ~~ Company ~~ Status ~~ Avios

Drop rules:
  - Status == "CANCELLED" (case-insensitive): DROP — Qatar keeps the cancelled
    redemption AND a paired refund row; the refund alone models the net.
  - Avios == 0: DROP — Qpoints/Qcredits-only events aren't spendable currency.

Classification:
  - Avios < 0 -> kind = 'redeem' (each award booking is its own row, kept
    separate by the shared collapser).
  - Avios > 0 -> kind = 'earn' (refunds, partner transfers, shopping earns —
    collapsed by (date, description) by shared code).

Description preference: use the Description column (it carries the booking
flight numbers + passenger names for redemptions / refunds, and the partner
detail for earnings). Fall back to Activity if Description is empty.

Usage: python3 transform.py raw.txt out_dir [from] [to] [balance]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from activity_output import write_activity, filter_by_period


def parse_avios(s):
    s = s.replace(',', '').replace('+', '').strip()
    try:
        return int(s)
    except Exception:
        return 0


def main():
    raw, out_dir = sys.argv[1], sys.argv[2]
    rfrom = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != '-' else None
    rto = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] != '-' else None
    bal = sys.argv[5] if len(sys.argv) > 5 else None
    rows = [l.split('~~') for l in open(raw).read().strip().split('\n') if l.strip()]
    out = []
    for parts in rows:
        if len(parts) < 6:
            continue
        date = parts[0].strip()
        activity = parts[1].strip()
        desc = parts[2].strip()
        # company = parts[3].strip()
        status = parts[4].strip()
        avios = parse_avios(parts[5])

        # Drop cancelled redemptions (refund row handles the net effect)
        if status.upper() == 'CANCELLED':
            continue
        # Drop zero-Avios rows (Qpoints/Qcredits-only)
        if avios == 0:
            continue

        # Description preference: full Description, fall back to Activity
        description = desc if desc else activity

        kind = 'redeem' if avios < 0 else 'earn'
        out.append((date, description, avios, kind))

    out = filter_by_period(out, rfrom, rto)
    write_activity('qatar', out, out_dir, rfrom, rto, bal)


if __name__ == '__main__':
    main()
