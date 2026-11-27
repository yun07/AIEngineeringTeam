"""Pure game logic and headless CLI for Snake.

This module contains no UI code and imports nothing beyond the standard
library (``random``, ``argparse``, ``json``, ``sys``). It is importable and
testable without a display, without ``tkinter`` and without a terminal: the
CLI only runs from ``main()`` under an ``if __name__ == "__main__"`` guard.

The public interface is normative: constants, the ``Game`` class with
``turn``, ``step``, ``snapshot``, ``from_state`` and the documented
properties.
"""

from __future__ import annotations

import argparse
import json
import random
import sys

GRID_WIDTH = 20
GRID_HEIGHT = 20
INITIAL_LENGTH = 3
FOOD_SCORE = 1
DIRECTIONS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}
OPPOSITE = {"U": "D", "D": "U", "L": "R", "R": "L"}

__all__ = [
    "GRID_WIDTH",
    "GRID_HEIGHT",
    "INITIAL_LENGTH",
    "FOOD_SCORE",
    "DIRECTIONS",
    "OPPOSITE",
    "Game",
    "main",
]

_MIN_SIZE = 3


def _is_int(value: object) -> bool:
    """True for real integers, excluding ``bool``."""
    return isinstance(value, int) and not isinstance(value, bool)


def _check_grid(width: object, height: object) -> None:
    if not _is_int(width):
        raise ValueError(f"width must be an int, got {width!r}")
    if not _is_int(height):
        raise ValueError(f"height must be an int, got {height!r}")
    if width < _MIN_SIZE:
        raise ValueError(f"width must be >= {_MIN_SIZE}, got {width!r}")
    if height < _MIN_SIZE:
        raise ValueError(f"height must be >= {_MIN_SIZE}, got {height!r}")


def _check_cell(cell: object, width: int, height: int, what: str) -> None:
    if not isinstance(cell, tuple) or len(cell) != 2:
        raise ValueError(f"{what} must be a (x, y) tuple, got {cell!r}")
    x, y = cell
    if not _is_int(x) or not _is_int(y):
        raise ValueError(f"{what} coordinates must be ints, got {cell!r}")
    if not (0 <= x < width and 0 <= y < height):
        raise ValueError(f"{what} {cell!r} is outside the {width}x{height} grid")


class Game:
    """Deterministic Snake game state machine.

    A single ``random.Random(seed)`` instance per ``Game`` is used only for
    food placement; there is no module-level randomness.
    """

    def __init__(
        self,
        width: int = GRID_WIDTH,
        height: int = GRID_HEIGHT,
        seed: int | None = None,
        initial_length: int = INITIAL_LENGTH,
    ) -> None:
        _check_grid(width, height)
        if not _is_int(initial_length):
            raise ValueError(f"initial_length must be an int, got {initial_length!r}")
        if initial_length < _MIN_SIZE:
            raise ValueError(
                f"initial_length must be >= {_MIN_SIZE}, got {initial_length!r}"
            )
        if initial_length > width:
            raise ValueError(
                f"initial_length must be <= width ({width}), got {initial_length!r}"
            )
        if seed is not None and not _is_int(seed):
            raise ValueError(f"seed must be an int or None, got {seed!r}")

        cy = height // 2
        head_x = max(width // 2, initial_length - 1)
        self._width = width
        self._height = height
        self._snake: list[tuple[int, int]] = [
            (head_x - i, cy) for i in range(initial_length)
        ]
        self._direction = "R"
        self._score = 0
        self._game_over = False
        self._rng = random.Random(seed)
        self._food: tuple[int, int] | None = self._spawn_food()
        if self._food is None:
            self._game_over = True

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    @classmethod
    def from_state(
        cls,
        *,
        width: int,
        height: int,
        snake: list[tuple[int, int]],
        food: tuple[int, int],
        direction: str = "R",
        score: int = 0,
        seed: int | None = None,
    ) -> "Game":
        """Build a ``Game`` in an explicit, validated state.

        Every violation raises ``ValueError`` before any instance exists.
        ``food`` is required and may never be ``None`` here.
        """
        _check_grid(width, height)

        if isinstance(snake, (str, bytes)) or not isinstance(snake, (list, tuple)):
            raise ValueError(f"snake must be a sequence of cells, got {snake!r}")
        cells = list(snake)
        if len(cells) < 1:
            raise ValueError("snake must contain at least one cell")
        if len(cells) > width * height:
            raise ValueError(
                f"snake has {len(cells)} cells, more than {width * height} grid cells"
            )
        seen: set[tuple[int, int]] = set()
        normalised: list[tuple[int, int]] = []
        for cell in cells:
            _check_cell(cell, width, height, "snake cell")
            if cell in seen:
                raise ValueError(f"snake cell {cell!r} is repeated")
            seen.add(cell)
            normalised.append((cell[0], cell[1]))

        _check_cell(food, width, height, "food")
        if food is not None and (food[0], food[1]) in seen:
            raise ValueError(f"food {food!r} lies on the snake")

        if not isinstance(direction, str) or direction not in DIRECTIONS:
            raise ValueError(
                f"direction must be exactly one of U, D, L, R, got {direction!r}"
            )

        if not _is_int(score):
            raise ValueError(f"score must be an int, got {score!r}")
        if score < 0:
            raise ValueError(f"score must be >= 0, got {score!r}")

        if seed is not None and not _is_int(seed):
            raise ValueError(f"seed must be an int or None, got {seed!r}")

        obj = cls.__new__(cls)
        obj._width = width
        obj._height = height
        obj._snake = normalised
        obj._food = (food[0], food[1])
        obj._direction = direction
        obj._score = score
        obj._game_over = False
        obj._rng = random.Random(seed)
        return obj

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------
    @property
    def width(self) -> int:
        """Grid width in cells."""
        return self._width

    @property
    def height(self) -> int:
        """Grid height in cells."""
        return self._height

    @property
    def score(self) -> int:
        """Current score, increased by ``FOOD_SCORE`` per food eaten."""
        return self._score

    @property
    def game_over(self) -> bool:
        """True once the snake hit a wall, itself, or filled the board."""
        return self._game_over

    @property
    def snake(self) -> list[tuple[int, int]]:
        """Snake cells, head first, as a fresh list."""
        return list(self._snake)

    @property
    def food(self) -> tuple[int, int] | None:
        """Current food cell, or ``None`` when the board is full."""
        return self._food

    @property
    def direction(self) -> str:
        """Current heading, one of ``U``, ``D``, ``L``, ``R``."""
        return self._direction

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def snapshot(self) -> dict:
        """Return a fresh dict describing the current state."""
        return {
            "snake": list(self._snake),
            "food": self._food,
            "score": self._score,
            "game_over": self._game_over,
            "direction": self._direction,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _inside(self, cell: tuple[int, int]) -> bool:
        x, y = cell
        return 0 <= x < self._width and 0 <= y < self._height

    def _spawn_food(self) -> tuple[int, int] | None:
        """Pick a uniformly random free cell, or ``None`` if the board is full."""
        occupied = set(self._snake)
        free = [
            (x, y)
            for y in range(self._height)
            for x in range(self._width)
            if (x, y) not in occupied
        ]
        if not free:
            return None
        return self._rng.choice(free)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------
    def turn(self, direction: str) -> bool:
        """Request a heading change. Returns True when the heading changed."""
        if not isinstance(direction, str):
            raise ValueError(f"direction must be a str, got {direction!r}")
        normalised = direction.strip().upper()
        if normalised not in DIRECTIONS:
            raise ValueError(
                f"direction must be one of U, D, L, R, got {direction!r}"
            )
        if self._game_over:
            return False
        if normalised == OPPOSITE[self._direction]:
            return False
        self._direction = normalised
        return True

    def step(self) -> dict:
        """Advance one tick and return the new snapshot."""
        if self._game_over:
            return self.snapshot()

        dx, dy = DIRECTIONS[self._direction]
        head_x, head_y = self._snake[0]
        new_head = (head_x + dx, head_y + dy)

        if not self._inside(new_head):
            self._game_over = True
            return self.snapshot()

        eating = new_head == self._food
        body = self._snake if eating else self._snake[:-1]
        if new_head in body:
            self._game_over = True
            return self.snapshot()

        if eating:
            self._snake = [new_head] + self._snake
            self._score += FOOD_SCORE
            self._food = self._spawn_food()
            if self._food is None:
                self._game_over = True
        else:
            self._snake = [new_head] + self._snake[:-1]

        return self.snapshot()


# ----------------------------------------------------------------------
# Headless CLI
# ----------------------------------------------------------------------
def _non_negative_int(text: str) -> int:
    """argparse type: an int >= 0."""
    try:
        value = int(text)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(f"expected an integer, got {text!r}")
    if value < 0:
        raise argparse.ArgumentTypeError(f"must be >= 0, got {value}")
    return value


def _positive_at_least_three_int(text: str) -> int:
    """argparse type: an int >= 3 (grid dimension)."""
    try:
        value = int(text)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(f"expected an integer, got {text!r}")
    if value < _MIN_SIZE:
        raise argparse.ArgumentTypeError(f"must be >= {_MIN_SIZE}, got {value}")
    return value


def _int_arg(text: str) -> int:
    """argparse type: any int (the seed)."""
    try:
        return int(text)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError(f"expected an integer, got {text!r}")


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for headless mode."""
    parser = argparse.ArgumentParser(
        prog="game.py",
        description="Headless deterministic Snake trace generator.",
    )
    parser.add_argument("--seed", type=_int_arg, required=True,
                        help="RNG seed (required, integer)")
    parser.add_argument("--ticks", type=_non_negative_int, required=True,
                        help="number of ticks to emit (required, >= 0)")
    parser.add_argument("--moves", default="",
                        help="turn characters applied before tick i+1")
    parser.add_argument("--width", type=_positive_at_least_three_int,
                        default=GRID_WIDTH, help="grid width (default 20)")
    parser.add_argument("--height", type=_positive_at_least_three_int,
                        default=GRID_HEIGHT, help="grid height (default 20)")
    parser.add_argument("--initial-length", type=_positive_at_least_three_int,
                        default=INITIAL_LENGTH,
                        help="initial snake length (default 3)")
    return parser


def _validate_moves(moves: str) -> None:
    """Raise ``ValueError`` if ``moves`` contains a non-direction character."""
    for index, char in enumerate(moves):
        if char not in DIRECTIONS:
            raise ValueError(
                f"invalid character {char!r} in --moves at index {index} "
                f"(allowed: U, D, L, R)"
            )


def format_trace_line(tick: int, snapshot: dict) -> str:
    """Render one trace line as JSON with the documented key order."""
    head = snapshot["snake"][0]
    food = snapshot["food"]
    record = {
        "tick": tick,
        "head": [head[0], head[1]],
        "length": len(snapshot["snake"]),
        "score": snapshot["score"],
        "food": None if food is None else [food[0], food[1]],
        "game_over": snapshot["game_over"],
    }
    return json.dumps(record)


def main(argv: list[str] | None = None) -> int:
    """Run the headless trace. Returns the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # Validate every semantic constraint before the first tick so a rejected
    # invocation produces zero trace lines.
    try:
        _validate_moves(args.moves)
        game = Game(
            width=args.width,
            height=args.height,
            seed=args.seed,
            initial_length=args.initial_length,
        )
    except ValueError as exc:
        print(f"game.py: error: {exc}", file=sys.stderr)
        return 2

    moves = args.moves
    lines: list[str] = []
    for tick in range(1, args.ticks + 1):
        index = tick - 1
        if index < len(moves):
            # turn() cannot fail here: _validate_moves already filtered input.
            game.turn(moves[index])
        snapshot = game.step()
        lines.append(format_trace_line(tick, snapshot))

    if lines:
        sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
