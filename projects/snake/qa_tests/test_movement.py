"""C2: one step advances the head exactly one cell."""

from game import Game


def test_c2_single_step_advances_head():
    g = Game.from_state(
        width=10,
        height=10,
        snake=[(5, 5), (4, 5), (3, 5)],
        food=(9, 9),
        direction="R",
        seed=1,
    )
    assert g.snake[0] == (5, 5)
    before_len = len(g.snake)
    snap = g.step()
    assert snap["snake"][0] == (6, 5)
    assert len(g.snake) == before_len == 3
    assert g.snake == [(6, 5), (5, 5), (4, 5)]
    assert g.game_over is False
    assert g.food == (9, 9)
    # a second step in the same direction advances one more cell
    g.step()
    assert g.snake[0] == (7, 5)
    assert len(g.snake) == 3
