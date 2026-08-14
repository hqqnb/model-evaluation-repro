#!/usr/bin/env python3
"""C10 黑盒评测：python3 test.py <candidate.py>"""

import importlib.util
import random
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

    # 1) 固定向量（由参考实现生成）
    vectors = [
        (b"hi", bytes.fromhex("7e0268697f0c7e")),
        (b"\x7e\x7d", bytes.fromhex("7e027d5e7d5d846c7e")),
        (b"\x00\x01\x02", bytes.fromhex("7e0300010213737e")),
    ]
    for payload, frame in vectors:
        got = mod.encode(payload)
        assert got == frame, f"encode mismatch: {got.hex()} != {frame.hex()}"
        assert mod.decode(frame) == payload
    score += 3

    # 2) 随机往返
    rng = random.Random(2026)
    for _ in range(1000):
        n = rng.randint(1, 255)
        payload = bytes(rng.randint(0, 255) for _ in range(n))
        frame = mod.encode(payload)
        assert mod.decode(frame) == payload
    score += 3

    # 3) 恶意帧必须报错
    base = bytes.fromhex("7e027d5e7d5d846c7e")  # payload = 0x7e 0x7d
    bad_frames = {
        "truncated": base[:-2],
        "wrong boundary": b"\x00" + base[1:-1] + b"\x00",
        "bad crc": base[:-3] + b"\x00" + base[-2:-1],
        "stray escape": bytes.fromhex("7e027d5e7d5d846c7d7e"),
        "bad escape": bytes.fromhex("7e027d5e7d5d847d407e"),
        "unescaped 0x7e": bytes.fromhex("7e027e7d5d846c7e"),
        "length mismatch": bytes.fromhex("7e037d5e7d5d846c7e"),
    }
    for name, frame in bad_frames.items():
        try:
            mod.decode(frame)
            raise AssertionError(f"malformed frame accepted: {name}")
        except ValueError:
            pass
    score += 4

    print(f"PASS  C10 score={score}/10")
    return 0


if __name__ == "__main__":
    sys.exit(main())
