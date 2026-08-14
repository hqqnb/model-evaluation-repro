#!/usr/bin/env python3
"""C1 黑盒评测：python3 test.py <candidate.py>"""

import importlib.util
import random
import signal
import sys
import time


def load(path):
    spec = importlib.util.spec_from_file_location("candidate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def brute(n, k, a):
    from collections import Counter

    out = []
    for i in range(n - k + 1):
        c = Counter(a[i : i + k])
        x = 0
        for v, t in c.items():
            if t % 2:
                x ^= v
        out.append(x)
    return out


def main():
    if len(sys.argv) != 2:
        print("usage: python3 test.py <candidate.py>")
        return 2
    mod = load(sys.argv[1])
    score = 0

    def deadline(signum, frame):
        raise TimeoutError("candidate timed out")

    old = signal.signal(signal.SIGALRM, deadline)
    signal.alarm(120)
    try:
        # 1) 样例
        got = mod.solve(5, 3, [1, 2, 2, 3, 3])
        assert got == [1, 3, 2], f"sample failed: {got}"
        score += 1

        # 2) 随机小数据对照暴力
        rng = random.Random(20260806)
        for _ in range(60):
            n = rng.randint(1, 40)
            k = rng.randint(1, n)
            a = [rng.randint(1, 12) for _ in range(n)]
            exp = brute(n, k, a)
            got = mod.solve(n, k, a)
            assert got == exp, f"random case failed n={n} k={k} a={a}\ngot={got}\nexp={exp}"
        score += 4

        # 3) 大数据正确性
        n, k = 1_000_000, 100_000
        rng = random.Random(7)
        a = [rng.randint(1, 10**9) for _ in range(n)]
        t0 = time.perf_counter()
        got = mod.solve(n, k, a)
        dt = time.perf_counter() - t0
        assert len(got) == n - k + 1
        score += 2

        # 4) 性能
        if dt > 8.0:
            print(f"FAIL: too slow ({dt:.2f}s > 8s)")
        else:
            score += 3

    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        return 1
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)

    print(f"PASS  C1 score={score}/10  time={dt:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
