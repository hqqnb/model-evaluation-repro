def last_less_than(a: list[int], target: int) -> int:
    lo, hi = 0, len(a) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] < target:
            lo = mid
        else:
            hi = mid
    return lo if a[lo] < target else -1
