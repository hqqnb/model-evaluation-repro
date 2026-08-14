from collections import Counter


def aggregate(path: str) -> list[tuple[str, str, int]]:
    cnt: Counter[tuple[str, str]] = Counter()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("|")
            if len(parts) != 4:
                continue
            _, level, node, _ = parts
            if level == "ERROR":
                cnt[(level, node)] += 1
    return sorted((lv, nd, c) for (lv, nd), c in cnt.items())
