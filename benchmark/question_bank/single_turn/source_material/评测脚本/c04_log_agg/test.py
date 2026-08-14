#!/usr/bin/env python3
"""C4 黑盒评测：python3 test.py <candidate.py>"""

import importlib.util
import os
import random
import signal
import sys
import tempfile
import time


def load(path):
    spec = importlib.util.spec_from_file_location("candidate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def gen(path, n, seed):
    rng = random.Random(seed)
    levels = ["INFO", "WARN", "ERROR"]
    nodes = [f"web-{i}" for i in range(1, 9)] + [f"api-{i}" for i in range(1, 5)]
    msgs = ["ok", "retry", "timeout", "disk full", "health check"]
    exp = {}
    with open(path, "w", encoding="utf-8") as f:
        for i in range(n):
            ts = 1700000000 + i
            lv = rng.choices(levels, weights=[70, 20, 10])[0]
            nd = rng.choice(nodes)
            msg = rng.choice(msgs)
            f.write(f"{ts}|{lv}|{nd}|{msg}\n")
            if lv == "ERROR":
                exp[(lv, nd)] = exp.get((lv, nd), 0) + 1
    return sorted((lv, nd, c) for (lv, nd), c in exp.items())


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
        with tempfile.TemporaryDirectory() as td:
            # 小文件 + 边界（空消息、无效行忽略）
            small = os.path.join(td, "small.log")
            with open(small, "w", encoding="utf-8") as f:
                f.write("1|INFO|web-1|start\n")
                f.write("2|ERROR|web-1|\n")
                f.write("badline\n")
                f.write("3|ERROR|api-1|x\n")
            assert mod.aggregate(small) == [("ERROR", "api-1", 1), ("ERROR", "web-1", 1)]
            score += 2

            # 中等随机正确性
            mid = os.path.join(td, "mid.log")
            exp = gen(mid, 20_000, 11)
            assert mod.aggregate(mid) == exp
            score += 3

            # 大数据
            big = os.path.join(td, "big.log")
            exp = gen(big, 500_000, 99)
            t0 = time.perf_counter()
            got = mod.aggregate(big)
            dt = time.perf_counter() - t0
            assert got == exp, "big output mismatch"
            score += 2

        if dt <= 4.0:
            score += 3
        else:
            print(f"FAIL: too slow ({dt:.2f}s > 4s)")

    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        return 1
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)

    print(f"PASS  C4 score={score}/10  time={dt:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
