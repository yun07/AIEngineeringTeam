"""C3 (negative): an invalid --moves character exits 2 with empty stdout
and exactly one non-empty stderr line, validated before any tick.
"""

from cli_support import run_cli


def _assert_rejected(proc):
    assert proc.returncode == 2, (proc.returncode, proc.stderr)
    assert proc.stdout == ""
    stderr_lines = proc.stderr.splitlines()
    assert len(stderr_lines) == 1
    assert stderr_lines[0].strip() != ""
    return stderr_lines[0]


def test_c3_invalid_move_character_exits_2():
    line = _assert_rejected(
        run_cli("--seed", "7", "--ticks", "3", "--moves", "RX")
    )
    assert "X" in line


def test_c3_invalid_move_char_is_rejected_with_large_tick_count():
    # Validation happens before tick 1, so even 500 ticks produce no output.
    _assert_rejected(
        run_cli("--seed", "7", "--ticks", "500", "--moves", "RRXDD")
    )


def test_c3_invalid_move_is_rejected_before_any_valid_prefix_runs():
    # "RRX": a valid prefix must not leak any tick line first.
    proc = run_cli("--seed", "7", "--ticks", "10", "--moves", "RRX")
    _assert_rejected(proc)
