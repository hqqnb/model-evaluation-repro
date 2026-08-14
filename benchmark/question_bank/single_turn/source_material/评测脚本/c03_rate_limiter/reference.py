import threading


class RateLimiter:
    def __init__(self, capacity: float, refill_per_second: float):
        self.capacity = capacity
        self.rate = refill_per_second
        self._lock = threading.Lock()
        self._buckets: dict[str, tuple[int, float]] = {}

    def try_acquire(self, key: str, tokens: float, now_ms: int) -> bool:
        with self._lock:
            last, cur = self._buckets.get(key, (now_ms, self.capacity))
            if now_ms < last:
                raise ValueError("now_ms must be monotonic")
            cur = min(self.capacity, cur + (now_ms - last) * self.rate / 1000.0)
            if cur + 1e-9 < tokens:
                self._buckets[key] = (now_ms, cur)
                return False
            self._buckets[key] = (now_ms, cur - tokens)
            return True
