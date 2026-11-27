"""C4 (negative): missing --seed/--ticks or negative --ticks is rejected
by argument validation with no trace lines on stdout.
"""

import pytest

from cli_support import run_cli


def _assert_no_trace(proc):
    assert proc.returncode != 0, (proc.returncode, proc.stdout)
    assert proc.stdout == ""
    assert proc.stderr.strip() != ""


@pytest.mark.parametrize(
    "args",
    [
        ("--ticks", "5"),                       # missing --seed
        ("--seed", "7"),                        # missing --ticks
        ("--seed", "7", "--ticks", "-1"),       # negative ticks
        ("--seed", "7", "--ticks", "-500"),     # negative ticks
        (),                                     # both missing
    ],
)
def test_c4_missing_or_negative_args_rejected(args):
    _assert_no_trace(run_cli(*args))


def test_c4_zero_ticks_is_valid_and_empty():
    proc = run_cli("--seed", "7", "--ticks", "0")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ""
