#!/usr/bin/env python3
"""C5 黑盒评测：python3 test.py <candidate.py>"""

import bisect
import importlib.util
import random
import runpy
import signal
import sys


def load(path):
    spec = importlib.util.spec_from_file_location("candidate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Deadline(Exception):
    pass


def alarm_handler(signum, frame):
    raise Deadline()


def main():
    if len(sys.argv) != 2:
        print("usage: python3 test.py <candidate.py>")
        return 2
    score = 0

    # 回归测试（候选文件 __main__ 里的 assert）必须通过
    try:
        runpy.run_path(sys.argv[1], run_name="__main__")
        score += 2
    except AssertionError:
        print("FAIL: candidate __main__ regression tests failed")

    mod = load(sys.argv[1])
    old = signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(10)
    try:
        cases = [
            ([], 5, -1),
            ([5], 5, -1),
            ([5], 6, 0),
            ([1, 3, 5], 5, 1),
            ([1, 3, 5], 4, 1),
            ([1, 3, 5], 0, -1),
            ([1, 3, 5], 10, 2),
            ([1, 2, 2, 2, 3], 3, 3),
            ([1, 2, 2, 2, 3], 2, 0),
            ([2, 2, 2, 2], 2, -1),
            ([2, 2, 2, 2], 3, 3),
        ]
        for a, t, exp in cases:
            got = mod.last_less_than(a, t)
            assert got == exp, f"case a={a} target={t}: got {got}, exp {exp}"
        score += 5

        rng = random.Random(5)
        for _ in range(30):
            n = rng.randint(1, 1000)
            a = sorted(rng.randint(1, 500) for _ in range(n))
            t = rng.randint(0, 600)
            exp = bisect.bisect_left(a, t) - 1
            got = mod.last_less_than(a, t)
            assert got == exp, f"random case: got {got}, exp {exp}"
        score += 3
    except Deadline:
        print("FAIL: infinite loop detected (deadline)")
        score = min(score, 2)
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        return 1
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)

    print(f"PASS  C5 score={score}/10")
    return 0


if __name__ == "__main__":
    sys.exit(main())
