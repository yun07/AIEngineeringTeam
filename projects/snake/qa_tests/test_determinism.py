"""C8: identical seeds give identical snapshot sequences."""

from game import Game

# "T<dir>" means turn, "S" means step.
SCRIPT = "TRSSTDSSTDSSSLSSSSSS"


def _ops(tokens):
    ops, i = [], 0
    while i < len(tokens):
        if tokens[i] == "T":
            ops.append(("turn", tokens[i + 1]))
            i += 2
        else:
            ops.append(("step", None))
            i += 1
    return ops


def _run(g):
    trace = [g.snapshot()]
    for kind, arg in _ops(SCRIPT):
        if kind == "turn":
            trace.append({"turn": g.turn(arg), "state": g.snapshot()})
        else:
            trace.append(g.step())
    return trace


def test_c8_same_seed_same_sequence():
    a = Game(width=8, height=8, seed=7, initial_length=3)
    b = Game(width=8, height=8, seed=7, initial_length=3)
    assert a.snapshot() == b.snapshot()
    assert _run(a) == _run(b)


def test_c8_from_state_same_seed_same_sequence():
    args = dict(
        width=6,
        height=6,
        snake=[(2, 2), (1, 2)],
        food=(3, 2),
        direction="R",
        seed=11,
    )
    a = Game.from_state(**args)
    b = Game.from_state(**args)
    for _ in range(6):
        assert a.snapshot() == b.snapshot()
        assert a.step() == b.step()
