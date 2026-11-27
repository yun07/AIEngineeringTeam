"""C3: eating food grows the snake, scores and respawns food."""

from game import FOOD_SCORE, Game


def test_c3_eating_grows_and_scores():
    g = Game.from_state(
        width=10,
        height=10,
        snake=[(4, 5), (3, 5), (2, 5)],
        food=(5, 5),
        direction="R",
        seed=3,
    )
    snap = g.step()
    assert len(g.snake) == 4
    assert g.score == FOOD_SCORE == 1
    assert g.snake[0] == (5, 5)
    assert g.snake[1] == (4, 5)
    assert g.snake[:4] == [(5, 5), (4, 5), (3, 5), (2, 5)]
    assert g.game_over is False
    assert g.food is not None
    assert g.food not in g.snake
    assert 0 <= g.food[0] < 10 and 0 <= g.food[1] < 10
    assert snap["score"] == 1 and len(snap["snake"]) == 4
