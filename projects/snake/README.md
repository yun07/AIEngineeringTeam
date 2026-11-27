# Snake

A small, dependency-free Snake game for Python 3.12, standard library only.

The project is split into two parts:

| File | Role |
|---|---|
| `game.py` | Pure game logic plus a deterministic headless CLI. No UI, no `tkinter`. |
| `app.py` | Optional, thin graphical renderer built on `tkinter`. |

All game rules — movement, growth, scoring, collision — live in `game.py`.
`app.py` only reads game state and draws it, so the game stays playable,
importable and testable with no display.

## Requirements

- Python 3.12 or newer.
- No third-party packages to install.
- `tkinter` is optional and only needed for the graphical mode.

## Play the graphical game

```bash
python app.py
```

A window opens with the board, the snake and the food.

Controls:

| Key | Action |
|---|---|
| Arrow keys or `W` `A` `S` `D` | Turn up / left / down / right |
| `R` | Restart |
| `Esc` | Quit |

The game ticks forward on its own. Eating food grows the snake by one cell and
adds one point. Hitting a wall or the snake's own body ends the game.

If `tkinter` is missing, or no display is available (for example over SSH or
in CI), `app.py` prints a short message and exits with status `1` without
raising. Use the headless mode in that case.

## Run the headless mode

The headless mode runs the game with no window and no `tkinter`, and prints a
deterministic trace:

```bash
python game.py --seed 7 --ticks 500
```

- `--seed <int>` — seed for food placement. Two runs with the same seed and the
  same options produce identical output.
- `--ticks <int>` — how many steps to simulate, for example `500`.

Example with the default seed:

```bash
python game.py --ticks 500
```

Because the headless mode never imports `tkinter`, it works on a machine with
no display and in CI.

## Using the logic as a library

```python
from game import Game

game = Game(seed=7)
game.step()
game.turn("U")
print(game.snapshot())
```

`snapshot()` returns a dict with the keys `snake`, `food`, `score`,
`game_over` and `direction`. `turn()` raises `ValueError` for an unknown
direction such as `"X"`.
