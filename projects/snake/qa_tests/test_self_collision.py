"""C5: self-collision ends the game; vacating tail cell is legal."""

from game import Game


def test_c5_self_collision_ends_game():
    g = Game.from_state(
        width=10,
        height=10,
        snake=[(3, 3), (3, 2), (2, 2), (2, 3), (2, 4)],
        food=(0, 9),
        direction="U",
    )
    assert g.turn("L") is True
    g.step()
    assert g.game_over is True
    assert g.snake == [(3, 3), (3, 2), (2, 2), (2, 3), (2, 4)]
    assert g.food == (0, 9)
    assert g.score == 0


def test_c5_vacating_tail_cell_is_legal():
    g = Game.from_state(
        width=10,
        height=10,
        snake=[(1, 2), (2, 2), (2, 3), (1, 3)],
        food=(5, 5),
        direction="R",
    )
    assert g.turn("D") is True
    g.step()
    assert g.game_over is False
    assert g.snake == [(1, 3), (1, 2), (2, 2), (2, 3)]
