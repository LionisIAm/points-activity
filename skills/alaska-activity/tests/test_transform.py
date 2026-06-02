"""
Unit test for the Alaska transform. Runs transform.py against the sanitized fixture and
asserts the unified CSV output and the reconciliation property. No live account needed.

Contract (v0.3): earnings collapse by (REAL date, description); redemptions/reversals
keep their real date, each its own row. Earlier versions collapsed earnings to the last
day of the month — this fixture/test now asserts per-date grouping.

Run:  python3 -m pytest skills/alaska-activity/tests/test_transform.py
   or: python3 skills/alaska-activity/tests/test_transform.py
"""
import csv, subprocess, sys, os, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
TRANSFORM = os.path.join(SKILL, 'scripts', 'transform.py')
FIXTURE = os.path.join(HERE, 'fixtures', 'raw_dump.txt')

EXPECTED_ROWS = [
    ('2026-03-15', 'SOME BANK CARD FOREIGN PURCHASE BONUS', '2000'),
    ('2026-03-15', 'SOME BANK CARD ACTIVITY', '5000'),
    ('2026-02-10', 'Partner Air XYZ-ABC ICODE John Doe', '-30000'),
    ('2026-02-10', 'Partner Air XYZ-ABC ICODE Jane Doe', '-30000'),
    ('2026-02-10', 'Partner Air Rollback: XYZ-ABC ICODE Jane Doe', '30000'),
    ('2026-01-20', 'POINTS.COM INSTANT POINTS', '35000'),
    ('2025-12-15', 'SOME BANK CARD ACTIVITY', '345'),
]
FAKE_BALANCE = 12345


def _run():
    out_dir = tempfile.mkdtemp()
    subprocess.run([sys.executable, TRANSFORM, FIXTURE, out_dir, '-', '-', str(FAKE_BALANCE)],
                   check=True, capture_output=True, text=True)
    csvs = [f for f in os.listdir(out_dir) if f.endswith('.csv')]
    assert len(csvs) == 1, f"expected one CSV, got {csvs}"
    fname = csvs[0]
    with open(os.path.join(out_dir, fname)) as f:
        rows = list(csv.reader(f))
    return fname, rows


def test_filename_uses_covered_range():
    fname, _ = _run()
    # covered range = oldest..newest actual rows (real dates, not month-end)
    assert fname == 'alaska_activity_2025-12-15_2026-03-15.csv', fname


def test_columns_and_rows():
    _, rows = _run()
    assert rows[0] == ['Date', 'Description', 'Amount']
    body = [tuple(r) for r in rows[1:]]
    assert body == [tuple(r) for r in EXPECTED_ROWS], body


def test_status_only_rows_dropped():
    # rows whose Total points is 0 (status-points-only) must not appear
    _, rows = _run()
    descs = [r[1] for r in rows[1:]]
    assert not any('STATUS POINTS ONLY' in d for d in descs)
    assert not any('2026 STATUS POINTS' in d for d in descs)


def test_reconciles_to_balance():
    # with the full window captured, sum(Amount) == balance (grouping-invariant)
    _, rows = _run()
    assert sum(int(r[2]) for r in rows[1:]) == FAKE_BALANCE


def test_rollback_nets_out_per_trip():
    # -30000 -30000 +30000 = -30000 net for the trip, each leg preserved as its own row
    _, rows = _run()
    trip = [int(r[2]) for r in rows[1:] if 'XYZ-ABC' in r[1]]
    assert sorted(trip) == [-30000, -30000, 30000]
    assert sum(trip) == -30000


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn(); print(f'PASS {name}')
    print('All tests passed.')
