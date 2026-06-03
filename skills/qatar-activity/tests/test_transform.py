"""
Unit test for the Qatar Airways (Privilege Club / Avios) transform. Runs transform.py
against the sanitized fixture and asserts the unified CSV. No live account needed.

Run:  python3 -m pytest skills/qatar-activity/tests/test_transform.py
   or: python3 skills/qatar-activity/tests/test_transform.py
"""
import csv, subprocess, sys, os, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
TRANSFORM = os.path.join(SKILL, 'scripts', 'transform.py')
FIXTURE = os.path.join(HERE, 'fixtures', 'raw_dump.txt')

EXPECTED_ROWS = [
    ('2026-05-24', 'Duty Free purchase', '121'),                  # 112 + 9 collapsed
    ('2026-03-07', 'Award Ticket ABC-DEF Passenger One', '-90000'),
    ('2026-01-19', 'Refund - Award Cancellation (X1Y2Z3)', '90000'),
    ('2025-04-10', 'Moved Avios to Privilege Club', '90000'),
]
FAKE_BALANCE = 90121


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
    assert fname == 'qatar_activity_2025-04-10_2026-05-24.csv', fname


def test_columns_and_rows():
    _, rows = _run()
    assert rows[0] == ['Date', 'Description', 'Amount']
    assert [tuple(r) for r in rows[1:]] == [tuple(r) for r in EXPECTED_ROWS]


def test_cancelled_redemption_dropped():
    # the CANCELLED award (GHI-JKL) must NOT appear — its paired refund models the net
    _, rows = _run()
    assert not any('GHI-JKL' in r[1] for r in rows[1:])


def test_qpoints_only_dropped():
    # Avios == 0 rows (Qpoints/Qcredits only) are not spendable currency
    _, rows = _run()
    assert not any('Qpoints only' in r[1] for r in rows[1:])


def test_reconciles_to_balance():
    _, rows = _run()
    assert sum(int(r[2]) for r in rows[1:]) == FAKE_BALANCE


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn(); print(f'PASS {name}')
    print('All tests passed.')
