#!/usr/bin/env python3
"""C2 黑盒评测：python3 test.py <candidate.py>"""

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
        d = mod.DSUKth([5, 1, 9, 3, 7])
        assert d.kth_largest(1, 1) == 5
        d.union(1, 3)
        d.union(3, 5)
        assert d.kth_largest(1, 1) == 9
        assert d.kth_largest(5, 2) == 7
        assert d.kth_largest(2, 1) == 1
        assert d.kth_largest(1, 9) == -1
        score += 2

        # 2) 随机小数据对照暴力
        rng = random.Random(42)
        for _ in range(40):
            n = rng.randint(1, 60)
            values = rng.sample(range(1, 10_000), n)
            d = mod.DSUKth(values)
            comps = [{i: {values[i]}} for i in range(n)]
            for step in range(300):
                op = rng.choice(["u", "q"])
                a = rng.randint(1, n)
                if op == "u":
                    b = rng.randint(1, n)
                    d.union(a, b)
                    sa = sb = None
                    for c in comps:
                        if a - 1 in c:
                            sa = c
                        if b - 1 in c:
                            sb = c
                    if sa is not sb:
                        sa.update(sb)
                        comps.remove(sb)
                else:
                    k = rng.randint(1, n + 3)
                    got = d.kth_largest(a, k)
                    c = next(c for c in comps if a - 1 in c)
                    vals = [v for s in c.values() for v in s]
                    exp = sorted(vals, reverse=True)[k - 1] if k <= len(vals) else -1
                    assert got == exp, f"mismatch step={step} a={a} k={k} got={got} exp={exp}"
        score += 6

        # 3) 大数据性能
        n = 200_000
        values = list(range(1, n + 1))
        d = mod.DSUKth(values)
        rng = random.Random(1)
        t0 = time.perf_counter()
        for _ in range(200_000):
            if rng.random() < 0.5:
                d.union(rng.randint(1, n), rng.randint(1, n))
            else:
                x = rng.randint(1, n)
                d.kth_largest(x, rng.randint(1, 5))
        dt = time.perf_counter() - t0
        if dt <= 15:
            score += 2
        else:
            print(f"FAIL: too slow ({dt:.2f}s)")

    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        return 1
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)

    print(f"PASS  C2 score={score}/10  time={dt:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
