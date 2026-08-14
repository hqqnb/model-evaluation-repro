#!/usr/bin/env python3
"""C3 黑盒评测：python3 test.py <candidate.py>"""

import importlib.util
import sys
import threading


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

    # 1) 单线程：容量与补充
    rl = mod.RateLimiter(capacity=5, refill_per_second=10)
    assert rl.try_acquire("k", 1, 0)
    assert rl.try_acquire("k", 4, 0)
    assert not rl.try_acquire("k", 1, 0)  # 空桶
    assert rl.try_acquire("k", 1, 500)    # 500ms 补充 5，够 1
    assert not rl.try_acquire("k", 5, 500)
    assert rl.try_acquire("k", 1, 1000)
    assert not rl.try_acquire("k", 100, 100_000)  # 不会超过 capacity
    score += 3

    # 2) key 独立
    rl = mod.RateLimiter(capacity=1, refill_per_second=0)
    assert rl.try_acquire("a", 1, 0)
    assert not rl.try_acquire("a", 1, 0)
    assert rl.try_acquire("b", 1, 0)
    score += 1

    # 3) 同 key 并发竞争：同一时刻只允许放行 capacity 个
    rl = mod.RateLimiter(capacity=1000, refill_per_second=0)
    lock = threading.Lock()
    accepted = [0]
    errors = []

    def racer():
        for _ in range(5000):
            try:
                if rl.try_acquire("race", 1, 0):
                    with lock:
                        accepted[0] += 1
            except Exception as e:  # noqa: BLE001
                errors.append(e)
                return

    threads = [threading.Thread(target=racer) for _ in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert not errors, f"exceptions: {errors[:3]}"
    assert accepted[0] == 1000, f"atomicity broken: accepted {accepted[0]}"
    score += 3

    # 4) 多 key 限速：每个 key 独立按速率补充，且不超容量
    rl = mod.RateLimiter(capacity=10, refill_per_second=1000)  # 1 token/ms
    accepted2 = [0]

    def filler(key, count):
        ok = 0
        for t in range(count):
            if rl.try_acquire(key, 1, t):
                ok += 1
        with lock:
            accepted2[0] += ok

    threads = [threading.Thread(target=filler, args=(f"k{i}", 100_000)) for i in range(8)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    per_key_max = 10 + 99_999  # 容量 + 全时段补充
    total = 8 * 100_000
    assert accepted2[0] <= 8 * per_key_max, f"over-issued: {accepted2[0]}"
    assert accepted2[0] >= total - 3000, f"too few accepted: {accepted2[0]}"
    score += 3

    print(f"PASS  C3 score={score}/10  race_ok={accepted[0]}/1000  total_ok={accepted2[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
