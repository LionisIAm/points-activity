"""
Unit test for the Bilt transform. Runs transform.py against the sanitized JSON fixture
and asserts the unified CSV output plus key behaviors. No live account needed.

Contract (v0.3): earnings collapse by (REAL date, description) — two dining earns on
DIFFERENT days stay separate (earlier versions collapsed them to one month-end row);
redemptions/transfers (tp<0) keep their real date, each its own row.

Run:  python3 -m pytest skills/bilt-activity/tests/test_transform.py
   or: python3 skills/bilt-activity/tests/test_transform.py
"""
import csv, subprocess, sys, os, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
TRANSFORM = os.path.join(SKILL, 'scripts', 'transform.py')
FIXTURE = os.path.join(HERE, 'fixtures', 'raw_dump.txt')

EXPECTED_ROWS = [
    ('2026-03-25', 'Some Store', '-150'),
    ('2026-03-20', '3x Points on Dining', '45'),
    ('2026-03-15', 'Additional 1X - Point Accelerator', '100'),
    ('2026-03-15', '2X Points on All Transactions', '200'),
    ('2026-03-10', '3x Points on Dining', '30'),
    ('2026-03-05', 'World of Hyatt', '-9000'),
    ('2026-03-05', 'World of Hyatt', '-9000'),
    ('2026-02-28', '3x Points on Dining', '60'),
]
FAKE_BALANCE = -17715  # sum of all tp in the fixture (grouping-invariant)


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
    assert fname == 'bilt_activity_2026-02-28_2026-03-25.csv', fname


def test_columns_and_rows():
    _, rows = _run()
    assert rows[0] == ['Date', 'Description', 'Amount']
    assert [tuple(r) for r in rows[1:]] == [tuple(r) for r in EXPECTED_ROWS]


def test_earnings_per_date_no_merchant():
    # "3x Points on Dining" earns land on three different days -> three separate rows
    # (per-date grouping never merges across dates). Merchant names never leak in.
    _, rows = _run()
    dining = sorted(r[0] for r in rows[1:] if r[1] == '3x Points on Dining')
    assert dining == ['2026-02-28', '2026-03-10', '2026-03-20'], dining
    descs = [r[1] for r in rows[1:]]
    assert 'Cafe One' not in descs and 'Cafe Two' not in descs and 'Shop X' not in descs


def test_multi_item_earning_split():
    # Shop X (tp 300) splits into its two benefit items, on the spend's real date
    _, rows = _run()
    body = [tuple(r) for r in rows[1:]]
    assert ('2026-03-15', '2X Points on All Transactions', '200') in body
    assert ('2026-03-15', 'Additional 1X - Point Accelerator', '100') in body


def test_redemptions_are_negative_and_dated():
    # anything with tp<0 (transfer or reversal) keeps its real date and own row
    _, rows = _run()
    body = [tuple(r) for r in rows[1:]]
    assert ('2026-03-05', 'World of Hyatt', '-9000') in body
    assert ('2026-03-25', 'Some Store', '-150') in body


def test_duplicate_redemptions_not_merged():
    # two identical -9000 World of Hyatt transfers on the same day stay as TWO rows
    _, rows = _run()
    hyatt = [r for r in rows[1:] if r[1] == 'World of Hyatt']
    assert len(hyatt) == 2
    assert all(r[2] == '-9000' for r in hyatt)


def test_zero_status_rows_dropped():
    _, rows = _run()
    assert not any('status' in r[1].lower() for r in rows[1:])


def test_reconciles_to_balance():
    _, rows = _run()
    assert sum(int(r[2]) for r in rows[1:]) == FAKE_BALANCE


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn(); print(f'PASS {name}')
    print('All tests passed.')
