"""C3 (negative): a README without the headless --seed/--ticks command fails.

Runs the C3 documentation assertions against a deliberately incomplete
README text, proving the check rejects documentation that omits the
headless command rather than passing vacuously.
"""

import re


def _documented_headless_command(text):
    for line in text.splitlines():
        if "game.py" not in line or not line.lstrip().startswith("python"):
            continue
        if "--seed" in line and "--ticks" in line:
            if re.search(r"--seed\s+\d+", line) and re.search(r"--ticks\s+\d+", line):
                return line
    return None


BAD_README = """# Snake

Run it with:

```bash
python app.py
```
"""

PARTIAL_README = """# Snake

```bash
python game.py --ticks 500
```
"""

GOOD_README = """# Snake

```bash
python game.py --seed 7 --ticks 500
```
"""


def test_c3_missing_headless_command_is_rejected():
    assert _documented_headless_command(BAD_README) is None
    assert _documented_headless_command(PARTIAL_README) is None


def test_c3_complete_headless_command_is_accepted():
    assert _documented_headless_command(GOOD_README) is not None


def test_c3_unseeded_seed_flag_without_value_is_rejected():
    text = "python game.py --seed --ticks 500\n"
    assert _documented_headless_command(text) is None
