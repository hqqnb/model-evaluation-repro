def last_less_than(a: list[int], target: int) -> int:
    lo, hi = 0, len(a) - 1
    ans = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if a[mid] < target:
            ans = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return ans
