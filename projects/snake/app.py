"""Optional thin tkinter renderer for Snake.

This module is optional. It must never be required to import or test the
game: ``tkinter`` is imported lazily *inside* ``main`` (and inside the
internal helpers that need it), so importing ``app`` succeeds on a machine
without a working tkinter, or on a headless machine with no display.

All game rules live in :mod:`game`. This module only reads ``Game`` state and
draws it; it contains no collision, growth or scoring logic.

Run the graphical game with::

    python app.py

Run the headless mode (no display, no tkinter) with::

    python game.py --seed 7 --ticks 500
"""

from __future__ import annotations

import game

__all__ = ["main"]

# Presentation-only constants; they have no effect on game rules.
CELL_SIZE = 24
TICK_MS = 120
BACKGROUND = "black"
SNAKE_COLOUR = "#3ddc84"
HEAD_COLOUR = "#1f8f52"
FOOD_COLOUR = "#e5484d"

# Key names understood by tkinter's <Key> binding, mapped to game directions.
_KEY_TO_DIRECTION = {
    "Up": "U",
    "w": "U",
    "W": "U",
    "Down": "D",
    "s": "D",
    "S": "D",
    "Left": "L",
    "a": "L",
    "A": "L",
    "Right": "R",
    "d": "R",
    "D": "R",
}


def _direction_for_key(keysym: str) -> str | None:
    """Map a tkinter key symbol to a game direction, or ``None``."""
    return _KEY_TO_DIRECTION.get(keysym)


def _draw(canvas, state: dict, cell_size: int = CELL_SIZE) -> None:
    """Redraw the whole board from a ``Game.snapshot()`` dict.

    Pure presentation: it reads ``snake`` and ``food`` and draws rectangles.
    """
    canvas.delete("all")
    width = canvas.winfo_width()
    height = canvas.winfo_height()
    canvas.create_rectangle(0, 0, width, height, fill=BACKGROUND, outline="")

    snake = state.get("snake") or []
    for index, (x, y) in enumerate(snake):
        x0 = x * cell_size
        y0 = y * cell_size
        canvas.create_rectangle(
            x0 + 1,
            y0 + 1,
            x0 + cell_size - 1,
            y0 + cell_size - 1,
            fill=HEAD_COLOUR if index == 0 else SNAKE_COLOUR,
            outline="",
        )

    food = state.get("food")
    if food is not None:
        fx, fy = food
        canvas.create_oval(
            fx * cell_size + 3,
            fy * cell_size + 3,
            fx * cell_size + cell_size - 3,
            fy * cell_size + cell_size - 3,
            fill=FOOD_COLOUR,
            outline="",
        )


def main(seed: int | None = None) -> int:
    """Launch the graphical game and return the process exit status.

    ``tkinter`` is imported here, inside the function body, so that
    ``import app`` never touches the optional dependency.

    Returns ``0`` on a normal exit, and ``1`` when tkinter or a display is
    unavailable, in which case a short message is printed and the caller can
    fall back to the headless mode.
    """
    try:
        import tkinter as tk
    except Exception:  # ImportError, or a broken/blocked _tkinter build.
        print(
            "tkinter is not available; run the headless mode instead:\n"
            "  python game.py --seed 7 --ticks 500"
        )
        return 1

    try:
        root = tk.Tk()
    except Exception:  # Typically tk.TclError: no display name and no $DISPLAY.
        print(
            "no graphical display available; run the headless mode instead:\n"
            "  python game.py --seed 7 --ticks 500"
        )
        return 1

    root.title("Snake")

    board = game.Game(seed=seed)
    width, height = board.width, board.height

    canvas = tk.Canvas(
        root,
        width=width * CELL_SIZE,
        height=height * CELL_SIZE,
        background=BACKGROUND,
        highlightthickness=0,
    )
    canvas.pack()

    status = tk.StringVar()
    status_label = tk.Label(root, textvariable=status, anchor="w")
    status_label.pack(fill="x")

    def refresh(message: str = "") -> None:
        state = board.snapshot()
        _draw(canvas, state)
        text = f"Score: {state['score']}"
        status.set(f"{text}  |  {message}" if message else text)

    def on_key(event) -> None:
        direction = _direction_for_key(event.keysym)
        if direction is None:
            return
        try:
            board.turn(direction)
        except ValueError:
            # Rejected input (e.g. reversing into the neck); state is unchanged.
            return

    def on_tick() -> None:
        if board.game_over:
            refresh("Game over - press R to restart, Esc to quit")
            return
        board.step()
        if board.game_over:
            refresh("Game over - press R to restart, Esc to quit")
            return
        refresh()
        root.after(TICK_MS, on_tick)

    def restart(_event=None) -> None:
        nonlocal board
        board = game.Game(seed=seed)
        refresh("Restarted")
        root.after(TICK_MS, on_tick)

    def quit_game(_event=None) -> None:
        root.destroy()

    root.bind("<Key>", on_key)
    root.bind("<Escape>", quit_game)
    root.bind("r", restart)
    root.bind("R", restart)

    refresh()
    root.after(TICK_MS, on_tick)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
