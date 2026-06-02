"""
Unit test for the Hilton Honors transform. Runs transform.py against the sanitized
fixture and asserts the unified CSV. No live account needed.

Note: the Hilton web feed exposes earnings + refunds only (no redemptions — a known
web glitch), so all rows here are positive credits and sum > a real spendable balance.
The fixture's FAKE_BALANCE equals the earnings sum on purpose.

Run:  python3 -m pytest skills/hilton-activity/tests/test_transform.py
   or: python3 skills/hilton-activity/tests/test_transform.py
"""
import csv, subprocess, sys, os, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
TRANSFORM = os.path.join(SKILL, 'scripts', 'transform.py')
FIXTURE = os.path.join(HERE, 'fixtures', 'raw_dump.txt')

EXPECTED_ROWS = [
    ('2026-05-13', 'Card Points on Eligible Spend', '639'),
    ('2026-05-13', 'Card Bonus Points', '2343'),
    ('2026-04-22', 'MEMBERSHIP REX UNITED STATES', '94000'),
    ('2025-09-12', 'Refund - Example Hotel', '380000'),
]
FAKE_BALANCE = 476982


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
    assert fname == 'hilton_activity_2025-09-12_2026-05-13.csv', fname


def test_columns_and_rows():
    _, rows = _run()
    assert rows[0] == ['Date', 'Description', 'Amount']
    assert [tuple(r) for r in rows[1:]] == [tuple(r) for r in EXPECTED_ROWS]


def test_zero_point_stay_dropped():
    _, rows = _run()
    assert not any('Example Hotel Stay' in r[1] for r in rows[1:])


def test_refund_kept_as_positive_credit():
    # refunds are positive credits, prefixed "Refund - " in the description
    _, rows = _run()
    refunds = [r for r in rows[1:] if r[1].startswith('Refund - ')]
    assert len(refunds) == 1 and int(refunds[0][2]) > 0


def test_reconciles_to_balance():
    _, rows = _run()
    assert sum(int(r[2]) for r in rows[1:]) == FAKE_BALANCE


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn(); print(f'PASS {name}')
    print('All tests passed.')
