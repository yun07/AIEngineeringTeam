"""C8: food placement is per-instance seeded, not module-level randomness."""

import game
from game import Game


def test_c8_food_placement_is_instance_seeded():
    # Module-level random must not influence food placement.
    import random as _random

    _random.seed(12345)
    a = Game(width=9, height=9, seed=42)
    _random.seed(999)
    b = Game(width=9, height=9, seed=42)
    assert a.food == b.food

    # Different seeds should be able to differ, and each stays off-snake.
    foods = set()
    for seed in range(12):
        g = Game(width=9, height=9, seed=seed)
        assert g.food not in g.snake
        foods.add(g.food)
    assert len(foods) > 1


def test_c8_respawn_sequence_is_reproducible():
    def run():
        g = Game.from_state(
            width=4,
            height=3,
            snake=[(0, 0)],
            food=(1, 0),
            direction="R",
            seed=5,
        )
        food_steps = [g.food]
        for _ in range(2):
            g.step()
            food_steps.append(g.food)
        return food_steps

    assert run() == run()
    assert hasattr(game, "Game")
