#!/usr/bin/env python3
"""
Shared READER for the unified points-activity CSV — the importer-side counterpart to
activity_output.py (the writer). Importers consume exactly what extractors produce, so
this is the single place that knows the CSV's shape on the read side.

This is the CANONICAL copy (under skills/points-activity/scripts/). Every *-import
skill ships a byte-identical copy in its own scripts/ dir; CI enforces that they match.
Do not diverge.

API:
  read_activity(csv_path) -> list[dict]
      Each dict: {'date': 'YYYY-MM-DD', 'description': str, 'amount': int}
      Amount is a signed int (earn +, redeem -). Rows preserve file order (newest-first).

  parse_summary(text) -> dict
      Parses the machine-readable lines an extractor prints to stdout:
        BALANCE: <int|unknown>   COVERED: <from>..<to>   REQUESTED: <...>
        FILE: <path>             ROWS: <n>
      Returns {'balance': int|None, 'covered_from': str|None, 'covered_to': str|None,
               'requested': str|None, 'file': str|None, 'rows': int|None}.

  split_kind(rows) -> (earns, redeems)
      Convenience: partition read_activity() rows by amount sign. Most api/mcp
      importers map earns -> income/credit and redeems -> expense/debit, but how
      (and whether) is each app's decision — see docs/ARCHITECTURE.md.
"""
import csv as _csv
import re as _re


def read_activity(csv_path):
    rows = []
    with open(csv_path, newline='') as f:
        for row in _csv.DictReader(f):
            amt = (row.get('Amount') or '').replace(',', '').strip()
            try:
                amt = int(amt)
            except ValueError:
                continue  # skip a malformed/blank amount rather than crash an import
            rows.append({
                'date': (row.get('Date') or '').strip(),
                'description': (row.get('Description') or '').strip(),
                'amount': amt,
            })
    return rows


def parse_summary(text):
    def grab(key):
        m = _re.search(rf'^{key}:\s*(.+?)\s*$', text or '', _re.M)
        return m.group(1).strip() if m else None

    bal = grab('BALANCE')
    covered = grab('COVERED') or ''
    cf, _, ct = covered.partition('..')
    rows = grab('ROWS')
    return {
        'balance': None if bal in (None, 'unknown', '') else int(bal),
        'covered_from': cf or None,
        'covered_to': ct or None,
        'requested': grab('REQUESTED'),
        'file': grab('FILE'),
        'rows': int(rows) if (rows and rows.isdigit()) else None,
    }


def split_kind(rows):
    earns = [r for r in rows if r['amount'] > 0]
    redeems = [r for r in rows if r['amount'] < 0]
    return earns, redeems
