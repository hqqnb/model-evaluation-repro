import heapq


class TaskScheduler:
    def __init__(self):
        self._seq = 0
        self._heap: list[tuple[int, int, str, str]] = []
        self._ids: set[str] = set()

    def enqueue(self, task_id: str, priority: int, payload: str) -> bool:
        if task_id in self._ids:
            return False
        self._ids.add(task_id)
        heapq.heappush(self._heap, (priority, self._seq, task_id, payload))
        self._seq += 1
        return True

    def dequeue(self):
        while self._heap:
            _, _, task_id, payload = heapq.heappop(self._heap)
            if task_id in self._ids:
                return (task_id, payload)
        return None

    def ack(self, task_id: str) -> None:
        self._ids.discard(task_id)
