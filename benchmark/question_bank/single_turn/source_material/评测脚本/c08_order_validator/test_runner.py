#!/usr/bin/env python3
"""C8 评测：python3 test_runner.py <candidate_tests.py>"""

import importlib.util
import os
import sys


HERE = os.path.dirname(os.path.abspath(__file__))


def load(path):
    spec = importlib.util.spec_from_file_location("candidate_tests", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(candidate_path, target):
    os.environ["TARGET_IMPL"] = target
    mod = load(candidate_path)
    failures = []
    for name in sorted(dir(mod)):
        if name.startswith("test_"):
            fn = getattr(mod, name)
            if callable(fn):
                try:
                    fn()
                except AssertionError as e:
                    failures.append((name, str(e)))
    return failures


def main():
    if len(sys.argv) != 2:
        print("usage: python3 test_runner.py <candidate_tests.py>")
        return 2
    cand = sys.argv[1]
    ref = os.path.join(HERE, "ref_impl.py")

    ref_fail = run(cand, ref)
    if ref_fail:
        print(f"FAIL: candidate tests produced false positives on correct impl: {ref_fail[:5]}")
        return 1
    score = 3

    variants = {
        "amount": "bug1_amount.py",
        "currency": "bug2_currency.py",
        "tolerance": "bug3_tolerance.py",
    }
    detected = []
    for name, fn in variants.items():
        if run(cand, os.path.join(HERE, fn)):
            detected.append(name)
    score += 2 * len(detected)
    if len(detected) == 3:
        score += 3
    score = min(score, 10)

    print(f"PASS  C8 score={score}/10  detected_bugs={detected}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
