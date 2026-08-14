#!/usr/bin/env python3
"""C7 黑盒评测：python3 test.py <candidate.py>"""

import importlib.util
import sys


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

    s = mod.TaskScheduler()
    assert s.dequeue() is None
    score += 1

    assert s.enqueue("t1", 2, "p1") is True
    assert s.enqueue("t1", 2, "p1-dup") is False  # 幂等去重
    assert s.enqueue("t2", 1, "p2") is True
    assert s.enqueue("t3", 1, "p3") is True
    score += 3

    assert s.dequeue() == ("t2", "p2")  # 高优先级先出
    assert s.dequeue() == ("t3", "p3")  # 同优先级 FIFO
    score += 2

    assert s.dequeue() == ("t1", "p1")
    assert s.dequeue() is None
    s.ack("t1")  # 已出队后 ack 不抛异常
    s.ack("no-such")  # 不存在不抛异常
    score += 2

    s.enqueue("t4", 0, "p4")
    s.ack("t4")
    assert s.dequeue() is None  # ack 后不再出队
    score += 2

    print(f"PASS  C7 score={score}/10")
    return 0


if __name__ == "__main__":
    sys.exit(main())
