"""C7 (negative): invalid directions raise ValueError with no mutation,
and every documented invalid constructor / from_state argument is rejected.
"""

import pytest

from game import Game

BAD = ["X", "", "UR", "u r", "\t", "RR", "1", "UD"]


@pytest.mark.parametrize("value", BAD)
def test_c7_invalid_direction_rejected(value):
    g = Game.from_state(
        width=10,
        height=10,
        snake=[(5, 5), (4, 5), (3, 5)],
        food=(0, 0),
        direction="R",
    )
    before = g.snapshot()
    with pytest.raises(ValueError):
        g.turn(value)
    assert g.snapshot() == before
    assert g.direction == "R"
    snap = g.snapshot()
    assert snap["snake"] == before["snake"]
    assert snap["food"] == before["food"]
    assert snap["score"] == before["score"]
    assert snap["game_over"] == before["game_over"]


def test_c7_invalid_direction_does_not_normalise_into_new_state():
    g = Game(seed=0)
    before = g.snapshot()
    for bad in ("x", " uu ", "lll"):
        with pytest.raises(ValueError):
            g.turn(bad)
        assert g.snapshot() == before
