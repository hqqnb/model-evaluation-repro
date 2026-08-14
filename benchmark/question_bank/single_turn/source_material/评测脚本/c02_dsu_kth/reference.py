from bisect import insort


class DSUKth:
    def __init__(self, values: list[int]):
        self.n = len(values)
        self.val = values[:]  # 0-indexed
        self.parent = list(range(self.n))
        self.size = [1] * self.n
        self.lists = [[v] for v in values]  # sorted lists at roots

    def find(self, x: int) -> int:
        x -= 1
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        small, big = self.lists[rb], self.lists[ra]
        for v in small:
            insort(big, v)
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        self.lists[rb] = None

    def kth_largest(self, x: int, k: int) -> int:
        r = self.find(x)
        lst = self.lists[r]
        if k < 1 or k > len(lst):
            return -1
        return lst[-k]
