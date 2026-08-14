from collections import Counter


def solve(n: int, k: int, a: list[int]) -> list[int]:
    cnt: dict[int, int] = {}
    acc = 0

    def add(x: int) -> None:
        nonlocal acc
        cnt[x] = cnt.get(x, 0) ^ 1
        acc ^= x if cnt[x] else x

    out = []
    for i in range(n):
        add(a[i])
        if i >= k:
            add(a[i - k])
        if i >= k - 1:
            out.append(acc)
    return out
