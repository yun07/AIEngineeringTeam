"""C1: --moves[i] is applied as turn() before tick i+1, so the first
emitted line is post-move.
"""

import json
import os
import sys

from cli_support import GAME_DIR, run_cli, trace_lines

sys.path.insert(0, GAME_DIR)
from game import Game  # noqa: E402


def _first_head(args, turns):
    proc = run_cli(*args)
    assert proc.returncode == 0, proc.stderr
    lines = trace_lines(proc)
    assert len(lines) == 1
    return json.loads(lines[0])["head"], turns


def test_c1_moves_applied_before_their_tick():
    # moves[0] == "U" applies before tick 1: head moves exactly one cell up.
    head, _ = _first_head(
        ("--seed", "7", "--ticks", "1", "--moves", "U"), ("U",)
    )
    g = Game(seed=7)
    start = g.snake[0]
    assert g.turn("U") is True
    g.step()
    assert head == list(g.snake[0])
    assert head == [start[0], start[1] - 1]

    # no --moves means the snake moves one cell right on tick 1
    head2, _ = _first_head(("--seed", "7", "--ticks", "1"), ())
    assert head2 == [start[0] + 1, start[1]]

    # second move applies before tick 2, not before tick 1
    proc = run_cli("--seed", "7", "--ticks", "2", "--moves", "RU")
    g2 = Game(seed=7)
    g2.turn("R")
    g2.step()
    tick1 = g2.snapshot()
    g2.turn("U")
    g2.step()
    tick2 = g2.snapshot()
    out = [json.loads(l) for l in trace_lines(proc)]
    assert out[0]["head"] == list(tick1["snake"][0])
    assert out[1]["head"] == list(tick2["snake"][0])
    assert os.path.basename(sys.executable)
