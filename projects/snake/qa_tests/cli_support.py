"""Shared helper: run the game.py headless CLI in a subprocess."""

import os
import subprocess
import sys

GAME_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cli(*extra):
    """Run `python game.py ...` and return CompletedProcess (text mode)."""
    argv = [sys.executable, "game.py", *extra]
    return subprocess.run(
        argv,
        cwd=GAME_DIR,
        capture_output=True,
        text=True,
        timeout=120,
    )


def trace_lines(proc):
    """Split stdout into lines, dropping only the trailing newline."""
    if proc.stdout == "":
        return []
    return proc.stdout.splitlines()
