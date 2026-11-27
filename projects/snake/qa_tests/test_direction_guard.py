"""C6: reversal rejected, legal turn accepted, no-op after game over."""

from game import Game


def test_c6_reversal_rejected():
    g = Game.from_state(
        width=10,
        height=10,
        snake=[(5, 5), (4, 5), (3, 5)],
        food=(0, 0),
        direction="R",
    )
    before = g.snapshot()
    assert g.turn("L") is False
    assert g.snapshot() == before
    assert g.direction == "R"
    assert g.snake == [(5, 5), (4, 5), (3, 5)]

    assert g.turn("R") is True
    assert g.direction == "R"
    assert g.turn("  d  ") is True
    assert g.direction == "D"


def test_c6_turn_false_after_game_over():
    g = Game.from_state(
        width=10,
        height=10,
        snake=[(0, 5), (1, 5), (2, 5)],
        food=(9, 0),
        direction="L",
    )
    g.step()
    assert g.game_over is True
    frozen = g.snapshot()
    assert g.turn("U") is False
    assert g.turn("D") is False
    assert g.snapshot() == frozen
