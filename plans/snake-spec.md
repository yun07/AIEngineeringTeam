# Snake Fixture Specification and QA Test Plan

- **Milestone:** M6 (`plans/phase1-architecture-plan.md`, section "M6 Snake specification and QA test plan"). This document is the specification only. It ships no code.
- **Authority:** [`plans/phase1-architecture-plan.md`](phase1-architecture-plan.md) owns milestone status, scope and acceptance. [`AI_Engineering_Team.md`](../AI_Engineering_Team.md) outranks it. This document must not contradict either; if it does, they win.
- **Purpose:** fix the requirement, the pure-logic interface, the deterministic headless mode and the exact QA test list, so that M7 can be judged mechanically by criterion ID.
- **Fixture scope:** Snake is the first end-to-end fixture only. Nothing in the engine may depend on Snake, on games or on a UI (plan Scope Statement). This document constrains `projects/snake/` only.

## 1. Requirement

The user request for the M7 run is the plan's request text (plan §B.1 step 1):

> Build a playable Snake game

In Phase 1 that request is satisfied by a **stdlib-only Python Snake game with a pure logic core and a deterministic headless mode**. A graphical window is optional and is never an acceptance gate.

Fixed constraints for the Developer:

- Python 3.12, standard library only. No third-party packages, no network access, no installation attempt.
- All files live under `projects/snake/`. Nothing is written outside that directory.
- The Developer has read, write and list tools only; it executes nothing. QA is the only role that runs commands.
- The game logic must be importable and testable without a display, without `tkinter`, and without a terminal.

## 2. Deliverables and ownership

| Path | Written by | Content |
|---|---|---|
| `projects/snake/game.py` | Developer | Pure game logic, headless CLI, no UI import at module load |
| `projects/snake/app.py` | Developer | Thin optional renderer; imports `tkinter` lazily inside a function |
| `projects/snake/README.md` | Developer | How to run the game and the headless mode |
| `projects/snake/qa_tests/test_*.py` | QA only | The tests in §6; QA never edits `game.py`, `app.py` or `README.md` |

QA writes no report file. The engine writes every report, including the QA evidence summary and the QA test file list used for the human spot check (plan §A.7 item 7, §F.2 item 13).

## 3. Pure-logic interface (`game.py`) — normative

The names, signatures and state transitions below are normative. QA tests target this interface, not the UI, not stdout formatting of `app.py`, and not internal attributes with a leading underscore.

### 3.1 Constants and defaults

```python
GRID_WIDTH = 20
GRID_HEIGHT = 20
INITIAL_LENGTH = 3
FOOD_SCORE = 1
DIRECTIONS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}
OPPOSITE = {"U": "D", "D": "U", "L": "R", "R": "L"}
```

### 3.2 Coordinates, grid and initial state

- A cell is an integer pair `(x, y)`. `x` increases rightwards, `y` increases downwards, both zero-based.
- A cell is inside the grid when `0 <= x < width` and `0 <= y < height`.
- `width >= 3`, `height >= 3` and `3 <= initial_length <= width` are required. A violating constructor argument raises `ValueError` and creates no instance.
- `cy = height // 2`. The head starts at `head_x = max(width // 2, initial_length - 1)` and the body extends leftwards, so the initial snake is
  `[(head_x, cy), (head_x - 1, cy), ..., (head_x - initial_length + 1, cy)]` — head first, exactly `initial_length` cells, pointing `"R"`.
  Because `head_x >= initial_length - 1`, the tail x is never negative, and because `head_x <= width - 1`, the head is always inside the grid. The formula is valid for every legal `width` and `initial_length`.
  Worked examples: `Game(20, 20)` → head `(10, 10)`, body `(9, 10)`, `(8, 10)`; `Game(width=3, height=3, initial_length=3)` → head `(2, 1)`, body `(1, 1)`, `(0, 1)`.
- The initial score is `0` and `game_over` is `False`.
- Food is one cell chosen uniformly at random from all in-grid cells that are **not** occupied by the snake, drawn from the instance RNG (§4). Food is never on the snake and is never `None` while a free cell exists. If no free cell exists at spawn time, `food` is `None` and `game_over` is `True`.

### 3.3 Class `Game`

```python
class Game:
    def __init__(self, width: int = GRID_WIDTH, height: int = GRID_HEIGHT,
                 seed: int | None = None,
                 initial_length: int = INITIAL_LENGTH) -> None: ...

    def turn(self, direction: str) -> bool: ...
    def step(self) -> dict: ...
    def snapshot(self) -> dict: ...

    @classmethod
    def from_state(cls, *, width: int, height: int,
                   snake: list[tuple[int, int]],
                   food: tuple[int, int],
                   direction: str = "R",
                   score: int = 0,
                   seed: int | None = None) -> "Game": ...

    @property
    def score(self) -> int: ...
    @property
    def game_over(self) -> bool: ...
    @property
    def snake(self) -> list[tuple[int, int]]: ...
    @property
    def food(self) -> tuple[int, int] | None: ...
    @property
    def direction(self) -> str: ...
```

`snapshot()` returns a new `dict` with exactly these keys, so callers cannot mutate game state through it:

```python
{"snake": [(x, y), ...], "food": (x, y) or None, "score": int,
 "game_over": bool, "direction": str}
```

### 3.4 Constructing states for tests (`from_state`)

QA must never reach into private state, and a check must not depend on a lucky random layout. Every scenario in §6 is built with either the public constructor or `Game.from_state` from §3.3. Rules for `from_state`:

1. `width >= 3` and `height >= 3`.
2. `snake` is head first and has `1 <= len(snake) <= width * height` cells. Every cell is inside the grid and no cell repeats.
3. `food` is inside the grid and is not on any snake cell. Food is never `None` at construction; a full board cannot be built this way.
4. `direction` is exactly one of `"U"`, `"D"`, `"L"`, `"R"`. No normalisation, so a test cannot silently rely on the leniency of `turn()`.
5. `score >= 0`. The score is accepted as given; `from_state` does not derive it from the snake length.
6. The instance starts with `game_over` false. Its RNG is created from `seed` and used only for the next food respawn, so a scenario stays deterministic after eating.
7. Any violation raises `ValueError` and creates no instance.

Game over is reached by playing a legal or colliding step, never by a setter. `from_state` is part of the contract, so the Developer must implement it and QA may rely on it.

### 3.5 `turn(direction)`

1. Normalise with `direction.strip().upper()`.
2. If the normalised value is not one of `"U"`, `"D"`, `"L"`, `"R"`, raise `ValueError`. **No state changes** and the exception is raised before any mutation.
3. If `game_over` is `True`, return `False` and change nothing.
4. If the normalised value is the opposite of the current direction, return `False` and change nothing (reversal into the neck is rejected).
5. Otherwise set the direction (repeating the current direction is allowed) and return `True`.

### 3.6 `step()`

1. If `game_over` is `True`, return `snapshot()` unchanged — a step after game over is a no-op.
2. `new_head = head + DIRECTIONS[direction]`, where `head` is `snake[0]`.
3. If `new_head` is outside the grid: set `game_over = True`, leave snake, food and score unchanged, return `snapshot()`.
4. `eating = (new_head == food)`.
5. `collision_body = snake` when `eating`, otherwise `snake[:-1]`. If `new_head` is in `collision_body`: set `game_over = True`, leave snake, food and score unchanged, return `snapshot()`. Excluding `snake[:-1]` when not eating is deliberate: the tail vacates its cell on the same tick, so entering that cell is legal.
6. If `eating`: prepend `new_head`, keep the tail (`snake = [new_head] + snake`), add `FOOD_SCORE` to the score, then respawn food per §3.2. If no free cell remains, `food = None` and `game_over = True`.
7. Otherwise: `snake = [new_head] + snake[:-1]`.
8. Return `snapshot()`.

`step()` never raises for normal play. It raises nothing at all except for programming errors outside this contract.

## 4. Determinism

- `Game` owns one `random.Random(seed)` instance, created by `__init__` or `from_state`, and used only for food placement. A `seed` of `None` means non-deterministic; every test and every headless run must pass an explicit integer seed.
- No module-level randomness, no `random.seed()` calls, no wall-clock, no environment or locale dependence.
- Same `seed`, same constructor arguments and same sequence of `turn()`/`step()` calls produce the same sequence of `snapshot()` values. The same holds for identical `from_state` arguments.

## 5. Headless mode (`game.py` CLI)

Invocation:

```
python game.py --seed 7 --ticks 500 [--moves "RRDDLL"] [--width 20] [--height 20] [--initial-length 3]
```

- `--seed` is required. `--ticks` is required and must be `>= 0`.
- `--moves` is optional. Character `i` (0-based) is applied as `turn(moves[i])` immediately before tick `i + 1`. When the string is exhausted, no further turns are applied.
- Output is exactly `--ticks` lines on stdout, one JSON object per line, and nothing else on stdout. Each line has these keys in this order:

```json
{"tick": 1, "head": [10, 10], "length": 3, "score": 0, "food": [4, 7], "game_over": false}
```

  `tick` is 1-based; `head` is `snake[0]`; `length` is `len(snake)`; `food` is `[x, y]` or `null`.
- Ticks always run to `--ticks` even after game over: post-game ticks repeat the final state, so the line count is deterministic.
- Exit code `0` when the trace is emitted.
- An invalid character in `--moves` (for example `"X"`) makes the CLI exit `2`, print a single diagnostic line to stderr, and emit no trace line.
- Validation runs before the first tick, so a rejected `--moves` value produces an empty stdout with zero trace lines.
- Determinism: same arguments produce byte-identical stdout.

## 6. QA test plan (exact list)

QA writes exactly these files and test functions. Node IDs are stable so the engine, the report and the human spot check refer to the same checks. Command for every check: `python -m pytest qa_tests -q` (one CONFIRM approval; QA may also run a single node during diagnosis, each executed with its own approval).

| Check | Criterion | `kind` | Test node | Assertion summary |
|---|---|---|---|---|
| K1 | C1 | positive | `qa_tests/test_initial_state.py::test_c1_initial_state` | `INITIAL_LENGTH` cells, all inside the grid; defaults give head `(10, 10)`, body `(9, 10)`, `(8, 10)`, direction `"R"`; the `width=3, height=3, initial_length=3` case gives head `(2, 1)` and body `(1, 1)`, `(0, 1)`; score `0`; `game_over` false; food is in-grid, not on the snake; `snapshot()` has exactly the keys in §3.3 |
| K2 | C2 | positive | `qa_tests/test_movement.py::test_c2_single_step_advances_head` | On a `(10, 10)` board with `seed=1`, one `step()` moves the head from `(5, 5)` to `(6, 5)`; length is unchanged when the head does not land on food |
| K3 | C3 | positive | `qa_tests/test_growth.py::test_c3_eating_grows_and_scores` | Build `Game.from_state(width=10, height=10, snake=[(4, 5), (3, 5), (2, 5)], food=(5, 5), direction="R", seed=3)`; one `step()`: length `4`, score `1`, head `(5, 5)`, `snake[1] == (4, 5)`, and the respawned food is not on any snake cell |
| K4 | C4 | positive | `qa_tests/test_wall_collision.py::test_c4_wall_collision_ends_game` | Build `Game.from_state(width=10, height=10, snake=[(0, 5), (1, 5), (2, 5)], food=(9, 0), direction="L")`; one `step()` sets `game_over` true with snake, food and score unchanged, and a further `step()` changes nothing |
| K5 | C5 | positive | `qa_tests/test_self_collision.py::test_c5_self_collision_ends_game` | Build `Game.from_state(width=10, height=10, snake=[(3, 3), (3, 2), (2, 2), (2, 3), (2, 4)], food=(0, 9), direction="U")`; `turn("L")` then `step()` sets `game_over` true; control case `Game.from_state(width=10, height=10, snake=[(1, 2), (2, 2), (2, 3), (1, 3)], food=(5, 5), direction="R")` turning `"D"` into the vacating tail cell does **not** end the game and yields snake `[(1, 3), (1, 2), (2, 2), (2, 3)]` |
| K6 | C6 | negative | `qa_tests/test_direction_guard.py::test_c6_reversal_rejected` | `turn("L")` on a right-moving snake returns `False`, leaves `direction` and `snake` unchanged; `turn("R")` returns `True`; after game over, `turn` returns `False` and changes nothing |
| **K7** | **C7** | **negative (designated)** | `qa_tests/test_negative_invalid_direction.py::test_c7_invalid_direction_rejected` | `turn("X")`, `turn("")` and `turn("UR")` each raise `ValueError`, and the snapshot is byte-equal before and after each attempt |
| K8 | C8 | positive | `qa_tests/test_headless_determinism.py::test_c8_headless_deterministic` | `python game.py --seed 7 --ticks 500 --moves "RRDDLLUU"` exits `0` with exactly 500 JSON lines and no exception; running it twice yields byte-identical stdout; two `Game(seed=7)` instances given the same call sequence yield identical snapshot sequences |
| K9 | C9 | positive | `qa_tests/test_app_import.py::test_c9_app_imports_without_renderer` | `import app` succeeds with `tkinter` absent or blocked; `app` exposes a `main` callable; the import emits no output and exits cleanly |
| **K10** | **C7** | **negative** | `qa_tests/test_negative_invalid_direction.py::test_c7_cli_invalid_move_exits_2` | `subprocess.run([sys.executable, "game.py", "--seed", "7", "--ticks", "3", "--moves", "RX"], capture_output=True, text=True)`: return code `2`, `stdout == ""` (zero trace lines), exactly one non-empty stderr line |

Rules for QA:

- Tests use only `pytest` from the standard test environment and the standard library. No new dependency, no installation, no network.
- Every test is deterministic and independent: explicit seeds, explicit board sizes, no dependence on the default grid for behaviour assertions.
- Every scenario is built with the public constructor or `Game.from_state` (§3.4). No test reads or writes a name starting with `_`, and no test relies on the CLI to create a special state.
- K7 is the designated negative case required by plan §F.2 item 8 and §F.3 item 21. The verdict check for K7 must carry `"criterion": "C7"` and `"kind": "negative"`. K6 and K10 are also marked `negative` because they assert rejection of invalid input.
- Every verdict check names its criterion ID, its `kind`, the executed command and the real exit code; the engine cross-checks them against the audit log (plan §A.7 items 5–6).

### 6.1 Criterion-to-check mapping (exit criterion for M6)

| Criterion | Planned check(s) | Covers |
|---|---|---|
| C1 | K1 | plan §F.3 item 15 |
| C2 | K2 | item 16 |
| C3 | K3 | item 17 |
| C4 | K4 | item 18 |
| C5 | K5 | item 19 |
| C6 | K6 | item 20 |
| C7 | K7 (negative, designated), K10 (negative, CLI) | item 21 |
| C8 | K8 | item 22 |
| C9 | K9 | item 23 |

Every criterion ID maps to at least one planned check. K7 is the single designated negative case, K10 is a second negative check of the same criterion at the CLI boundary, and K6 is marked negative because it asserts rejection of invalid input. A human can verify both statements by reading this table and §6.

## 7. Acceptance criteria (stable IDs)

| ID | Criterion |
|---|---|
| C1 | Initial state: snake length is at least three, fully inside the grid, food placed on a free cell, `snapshot()` exposing the documented keys |
| C2 | Movement: each tick advances the head exactly one cell in the current direction |
| C3 | Growth: eating food increases length by one and score by one, and respawns food off the body |
| C4 | Wall collision ends the game with `game_over` true |
| C5 | Self-collision ends the game when the head enters a body cell, while entering the vacating tail cell does not |
| C6 | Direction reversal into the immediate neck is rejected with no state change |
| C7 | Invalid direction input is rejected: `turn()` raises `ValueError` with no state mutation, and the CLI exits `2` with empty stdout for an invalid `--moves` character (the designated negative case) |
| C8 | Headless mode is deterministic: identical arguments give identical traces, and 500 ticks complete without exceptions |
| C9 | `app.py` imports without the optional renderer; `tkinter` is not required for acceptance |

## 8. Out of scope

- No engine, provider, agent, prompt or config change. M6 is a documentation milestone.
- No file is created under `projects/snake/` by M6; the Developer creates them in M7.
- Windows, colours, sound, score persistence, levels, obstacles and multiplayer are not required and are not acceptance criteria.
- `app.py` visual correctness is a human spot check only; it is never an automated gate.
- This document does not authorise commit, push, merge, a live run or any code change.
