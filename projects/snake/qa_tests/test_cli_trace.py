"""C1: the headless CLI emits exactly --ticks JSON lines on stdout."""

import json

from cli_support import run_cli, trace_lines

KEYS = ["tick", "head", "length", "score", "food", "game_over"]
ARGS = ("--seed", "7", "--ticks", "500", "--moves", "RRDDLLUU")


def test_c1_cli_emits_500_wellformed_lines():
    proc = run_cli(*ARGS)
    assert proc.returncode == 0, proc.stderr
    assert proc.stderr == ""
    lines = trace_lines(proc)
    assert len(lines) == 500
    # nothing else on stdout: no blank lines, no extra text
    assert proc.stdout.endswith("\n")
    assert all(line.strip() for line in lines)

    objs = [json.loads(line) for line in lines]
    for i, obj in enumerate(objs, start=1):
        assert list(obj.keys()) == KEYS
        assert obj["tick"] == i
        assert len(obj["head"]) == 2
        assert 0 <= obj["head"][0] < 20 and 0 <= obj["head"][1] < 20
        assert 3 <= obj["length"] <= 400
        assert obj["food"] is None or len(obj["food"]) == 2
        assert isinstance(obj["score"], int)
        assert isinstance(obj["game_over"], bool)


def test_c1_key_order_is_exact_and_nonempty():
    proc = run_cli("--seed", "7", "--ticks", "2")
    assert proc.returncode == 0, proc.stderr
    lines = trace_lines(proc)
    assert len(lines) == 2
    for line in lines:
        assert list(json.loads(line).keys()) == KEYS
    # the raw text order matches the documented key order
    for key in KEYS:
        assert ('"%s"' % key) in lines[0]
    positions = [lines[0].index('"%s"' % k) for k in KEYS]
    assert positions == sorted(positions)
