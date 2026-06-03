"""
Unit test for the Flying Blue transform. Runs transform.py against the sanitized fixture
and asserts the unified CSV. No live account needed.

Run:  python3 -m pytest skills/flyingblue-activity/tests/test_transform.py
   or: python3 skills/flyingblue-activity/tests/test_transform.py
"""
import csv, subprocess, sys, os, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
TRANSFORM = os.path.join(SKILL, 'scripts', 'transform.py')
FIXTURE = os.path.join(HERE, 'fixtures', 'raw_dump.txt')

EXPECTED_ROWS = [
    ('2026-02-24', 'SFO - CDG - BCN, Passenger Two', '-60000'),
    ('2026-02-24', 'SFO - CDG - BCN, Passenger One', '-60000'),
    ('2025-11-23', 'AMERICAN EXPRESS MEMBERSHIP REWARD MILES', '110000'),
    ('2025-09-04', 'Hotel partner MILES+POINTS', '80'),    # 31 + 49 collapsed (same date+desc)
    ('2025-06-08', 'Status match bonus', '10000'),
]
FAKE_BALANCE = 80


def _run():
    out_dir = tempfile.mkdtemp()
    subprocess.run([sys.executable, TRANSFORM, FIXTURE, out_dir, '-', '-', str(FAKE_BALANCE)],
                   check=True, capture_output=True, text=True)
    csvs = [f for f in os.listdir(out_dir) if f.endswith('.csv')]
    assert len(csvs) == 1, f"expected one CSV, got {csvs}"
    with open(os.path.join(out_dir, csvs[0])) as f:
        return csvs[0], list(csv.reader(f))


def test_filename_uses_covered_range():
    fname, _ = _run()
    assert fname == 'flyingblue_activity_2025-06-08_2026-02-24.csv', fname


def test_columns_and_rows():
    _, rows = _run()
    assert rows[0] == ['Date', 'Description', 'Amount']
    assert [tuple(r) for r in rows[1:]] == [tuple(r) for r in EXPECTED_ROWS]


def test_redemptions_kept_separate():
    # two award legs on the same date stay as TWO rows (matched to passengers later)
    _, rows = _run()
    legs = [r for r in rows[1:] if r[1].startswith('SFO - CDG - BCN')]
    assert len(legs) == 2 and all(r[2] == '-60000' for r in legs)


def test_earn_collapsed_same_date_desc():
    _, rows = _run()
    mp = [r for r in rows[1:] if r[1] == 'Hotel partner MILES+POINTS']
    assert len(mp) == 1 and mp[0][2] == '80'


def test_reconciles_to_balance():
    _, rows = _run()
    assert sum(int(r[2]) for r in rows[1:]) == FAKE_BALANCE


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn(); print(f'PASS {name}')
    print('All tests passed.')
