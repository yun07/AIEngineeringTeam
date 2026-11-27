"""C2: identical CLI arguments give byte-identical stdout; ticks continue
to the full count after game over by repeating the final state.
"""

import json

from cli_support import run_cli, trace_lines

ARGS = ("--seed", "7", "--ticks", "500", "--moves", "RRDDLLUU")


def test_c2_two_runs_are_byte_identical():
    a = run_cli(*ARGS)
    b = run_cli(*ARGS)
    assert a.returncode == 0, a.stderr
    assert b.returncode == 0, b.stderr
    assert a.stdout == b.stdout
    assert a.stdout.encode() == b.stdout.encode()
    assert len(trace_lines(a)) == 500
    assert len(trace_lines(b)) == 500


def test_c2_ticks_continue_after_game_over_repeating_final_state():
    # Small board, long straight run into the wall -> guaranteed game over.
    proc = run_cli(
        "--seed", "1", "--ticks", "40", "--width", "5", "--height", "5",
        "--initial-length", "3",
    )
    assert proc.returncode == 0, proc.stderr
    lines = trace_lines(proc)
    assert len(lines) == 40
    objs = [json.loads(line) for line in lines]
    assert [o["tick"] for o in objs] == list(range(1, 41))

    over = [i for i, o in enumerate(objs) if o["game_over"]]
    assert over, "expected the snake to hit the wall on a 5x5 board"
    first_over = objs[over[0]]
    for later in objs[over[0]:]:
        assert later["game_over"] is True
        assert later["head"] == first_over["head"]
        assert later["length"] == first_over["length"]
        assert later["score"] == first_over["score"]
        assert later["food"] == first_over["food"]
