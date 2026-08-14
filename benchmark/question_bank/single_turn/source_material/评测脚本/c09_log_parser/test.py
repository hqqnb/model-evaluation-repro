#!/usr/bin/env python3
"""C9 黑盒评测：python3 test.py <candidate.py>"""

import importlib.util
import sys


def load(path):
    spec = importlib.util.spec_from_file_location("candidate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CASES = [
    (
        '单行正常',
        '[2026-08-06 12:00:00.123] LVL=INFO NODE=web-1 MSG="hello"',
        ([("2026-08-06 12:00:00.123", "INFO", "web-1", "hello")], []),
    ),
    (
        '转义序列',
        '[2026-08-06 12:00:00.123] LVL=WARN NODE=api-2 MSG="say \\"hi\\" and \\\\ and \\n newline"',
        ([("2026-08-06 12:00:00.123", "WARN", "api-2", 'say "hi" and \\ and \n newline')], []),
    ),
    (
        '消息内真实换行',
        '[2026-08-06 12:00:00.123] LVL=INFO NODE=web-1 MSG="line1\nline2"',
        ([("2026-08-06 12:00:00.123", "INFO", "web-1", "line1\nline2")], []),
    ),
    (
        'UTF-8 中文与 emoji',
        '[2026-08-06 12:00:00.123] LVL=ERROR NODE=worker-3 MSG="中文 🚀 测试"',
        ([("2026-08-06 12:00:00.123", "ERROR", "worker-3", "中文 🚀 测试")], []),
    ),
    (
        '空消息',
        '[2026-08-06 12:00:00.123] LVL=INFO NODE=x MSG=""',
        ([("2026-08-06 12:00:00.123", "INFO", "x", "")], []),
    ),
    (
        '多行多记录混合',
        '[2026-08-06 12:00:00.123] LVL=INFO NODE=web-1 MSG="ok"\n'
        '\n'
        '[bad] LVL=INFO NODE=x MSG="a"\n'
        '[2026-08-06 12:00:00.123] LVL=DEBUG NODE=x MSG="a"\n'
        '[2026-08-06 12:00:00.123] LVL=INFO NODE=x MSG="ok" trailing\n'
        'garbage\n'
        '[2026-08-06 12:00:00.124] LVL=ERROR NODE=y MSG="multi\n'
        'line\\nend"\n'
        '[2026-08-06 12:00:00.125] LVL=INFO NODE=z MSG="unclosed',
        (
            [
                ("2026-08-06 12:00:00.123", "INFO", "web-1", "ok"),
                ("2026-08-06 12:00:00.124", "ERROR", "y", "multi\nline\nend"),
            ],
            [
                (3, "bad timestamp"),
                (4, "invalid level"),
                (5, "trailing content"),
                (6, "invalid header"),
                (9, "unclosed quote"),
            ],
        ),
    ),
    (
        '空输入',
        "",
        ([], []),
    ),
]


def main():
    if len(sys.argv) != 2:
        print("usage: python3 test.py <candidate.py>")
        return 2
    mod = load(sys.argv[1])
    score = 0
    for name, data, exp in CASES:
        got = mod.parse_log(data)
        if got == exp:
            score += 1
        else:
            print(f"FAIL case: {name}\n got={got}\n exp={exp}")
    print(f"PASS  C9 score={score}/{len(CASES)}")
    return 0 if score == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
