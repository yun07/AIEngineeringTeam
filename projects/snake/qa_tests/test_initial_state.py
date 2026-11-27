"""C1: default initial state, documented keys and food placement."""

import game
from game import Game


def _inside(cell, w, h):
    return 0 <= cell[0] < w and 0 <= cell[1] < h


def test_c1_initial_state():
    assert game.INITIAL_LENGTH == 3
    assert game.GRID_WIDTH == 20 and game.GRID_HEIGHT == 20
    assert game.FOOD_SCORE == 1
    assert game.DIRECTIONS == {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}
    assert game.OPPOSITE == {"U": "D", "D": "U", "L": "R", "R": "L"}

    g = Game(seed=0)
    assert len(g.snake) == game.INITIAL_LENGTH
    assert all(_inside(c, 20, 20) for c in g.snake)
    assert g.snake[0] == (10, 10)
    assert g.snake[1] == (9, 10)
    assert g.snake[2] == (8, 10)
    assert g.direction == "R"
    assert g.score == 0
    assert g.game_over is False
    assert g.food is not None
    assert _inside(g.food, 20, 20)
    assert g.food not in g.snake

    snap = g.snapshot()
    assert set(snap.keys()) == {"snake", "food", "score", "game_over", "direction"}

    # snapshot is a fresh copy: mutating it must not touch state
    snap["snake"].append((0, 0))
    snap["score"] = 99
    assert len(g.snake) == 3 and g.score == 0

    small = Game(width=3, height=3, initial_length=3, seed=1)
    assert small.snake == [(2, 1), (1, 1), (0, 1)]

    # food differs across seeds for at least some seeds (off-snake guarantee)
    for seed in range(5):
        gs = Game(seed=seed)
        assert gs.food is not None and gs.food not in gs.snake
