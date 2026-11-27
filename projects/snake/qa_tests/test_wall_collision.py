"""C4: wall collision ends the game and freezes state."""

from game import Game


def test_c4_wall_collision_ends_game():
    g = Game.from_state(
        width=10,
        height=10,
        snake=[(0, 5), (1, 5), (2, 5)],
        food=(9, 0),
        direction="L",
    )
    snap = g.step()
    assert g.game_over is True
    assert snap["game_over"] is True
    assert g.snake == [(0, 5), (1, 5), (2, 5)]
    assert g.food == (9, 0)
    assert g.score == 0

    frozen = g.snapshot()
    after = g.step()
    assert g.game_over is True
    assert after == frozen
    assert g.snake == [(0, 5), (1, 5), (2, 5)]
    assert g.food == (9, 0)
    assert g.score == 0
