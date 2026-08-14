"""O(n^2) 反例：逐对统计，500k 行无法按时完成。"""


def aggregate(path: str) -> list[tuple[str, str, int]]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            ts, level, node, msg = line.rstrip("\n").split("|")
            rows.append((level, node))
    uniq = sorted(set(rows))
    out = []
    for lv, nd in uniq:
        c = rows.count((lv, nd))
        out.append((lv, nd, c))
    return out
