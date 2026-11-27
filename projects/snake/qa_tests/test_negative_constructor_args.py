"""C7 (negative): constructor and from_state reject invalid arguments."""

import pytest

from game import Game


def test_constructor_rejects_invalid_arguments():
    bad_kwargs = [
        {"width": 2, "height": 10},
        {"width": 10, "height": 2},
        {"width": 10, "height": 10, "initial_length": 2},
        {"width": 5, "height": 10, "initial_length": 6},
    ]
    for kwargs in bad_kwargs:
        with pytest.raises(ValueError):
            Game(**kwargs)


def test_from_state_rejects_invalid_arguments():
    good = dict(
        width=10,
        height=10,
        snake=[(5, 5), (4, 5), (3, 5)],
        food=(0, 0),
    )
    built = Game.from_state(**good)  # sanity: the baseline builds
    assert built.snake == [(5, 5), (4, 5), (3, 5)]

    bad_kwargs = [
        {"width": 2},
        {"height": 2},
        {"snake": []},
        {"snake": [(5, 5), (5, 5)]},
        {"snake": [(10, 5), (4, 5)]},
        {"snake": [(5, 5), (4, -1)]},
        {"food": (5, 5)},
        {"food": (10, 0)},
        {"food": (0, -1)},
        {"direction": "X"},
        {"direction": "r"},
        {"direction": " R"},
        {"score": -1},
    ]
    for patch in bad_kwargs:
        kwargs = dict(good, **patch)
        with pytest.raises(ValueError):
            Game.from_state(**kwargs)
