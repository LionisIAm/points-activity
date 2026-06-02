"""
TEMPLATE unit test — runs the example transform against the sanitized fixture and
asserts the unified CSV. Runnable as-is (the example program), so a contributor can
verify the pipeline before adapting. When you adapt the skill, rewrite EXPECTED_ROWS
and FAKE_BALANCE for your fixture.

Demonstrates the contract guarantees a real program should also test:
  - earnings with the same (date, description) collapse and sum;
  - redemptions stay one row each (duplicates NOT merged);
  - zero-amount rows are dropped;
  - sum(Amount) reconciles to the (fake) balance.

Run:  python3 -m pytest templates/activity-skill/tests/test_transform.py
   or: python3 templates/activity-skill/tests/test_transform.py
"""
import csv, subprocess, sys, os, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
TRANSFORM = os.path.join(SKILL, 'scripts', 'transform.py')
FIXTURE = os.path.join(HERE, 'fixtures', 'raw_dump.txt')

EXPECTED_ROWS = [
    ('2026-03-15', 'Card Spend Bonus', '750'),       # 500 + 250 collapsed (same date+desc)
    ('2026-03-10', 'Welcome Bonus', '20000'),
    ('2026-02-20', 'Award Flight ABC-XYZ', '-8000'),  # two identical redemptions stay
    ('2026-02-20', 'Award Flight ABC-XYZ', '-8000'),  # as TWO separate rows
]
FAKE_BALANCE = 4750  # 750 + 20000 - 8000 - 8000


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
    assert fname == 'example_activity_2026-02-20_2026-03-15.csv', fname


def test_columns_and_rows():
    _, rows = _run()
    assert rows[0] == ['Date', 'Description', 'Amount']
    assert [tuple(r) for r in rows[1:]] == [tuple(r) for r in EXPECTED_ROWS]


def test_zero_rows_dropped():
    _, rows = _run()
    assert not any('Status Credit' in r[1] for r in rows[1:])


def test_duplicate_redemptions_not_merged():
    _, rows = _run()
    awards = [r for r in rows[1:] if r[1] == 'Award Flight ABC-XYZ']
    assert len(awards) == 2 and all(r[2] == '-8000' for r in awards)


def test_reconciles_to_balance():
    _, rows = _run()
    assert sum(int(r[2]) for r in rows[1:]) == FAKE_BALANCE


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn(); print(f'PASS {name}')
    print('All tests passed.')
