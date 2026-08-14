#!/usr/bin/env python3
"""C6 黑盒评测：python3 test.py <candidate.py>"""

import importlib.util
import os
import stat
import subprocess
import sys
import tempfile


def load(path):
    spec = importlib.util.spec_from_file_location("candidate", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    if len(sys.argv) != 2:
        print("usage: python3 test.py <candidate.py>")
        return 2
    cand = open(sys.argv[1], encoding="utf-8").read()
    src = load(sys.argv[1])
    score = 0

    with tempfile.TemporaryDirectory() as td:
        reports = os.path.join(td, "reports")
        os.makedirs(os.path.join(reports, "sub"))
        secret = os.path.join(td, "secret.txt")
        with open(secret, "w") as f:
            f.write("TOP-SECRET")
        with open(os.path.join(reports, "report.txt"), "w") as f:
            f.write("hello")
        with open(os.path.join(reports, "sub", "inner.txt"), "w") as f:
            f.write("inner")
        os.symlink(secret, os.path.join(reports, "link.txt"))

        # 合法读取
        assert src.load_report("report.txt", reports) == "hello"
        assert src.load_report("sub/inner.txt", reports) == "inner"
        score += 1

        # 攻击载荷必须拒绝
        for bad in ["../secret.txt", "../../etc/passwd", "/etc/passwd", "link.txt", "..", "reports/../../secret.txt"]:
            try:
                src.load_report(bad, reports)
                raise AssertionError(f"path traversal not rejected: {bad}")
            except ValueError:
                pass
        score += 4

        # 命令注入
        bin_dir = os.path.join(td, "bin")
        os.makedirs(bin_dir)
        fake = os.path.join(bin_dir, "export_data")
        with open(fake, "w") as f:
            f.write("#!/bin/sh\nprintf 'OK %s\\n' \"$1\" > \"$FAKE_OUT\"\n")
        os.chmod(fake, stat.S_IRWXU)
        pwn = os.path.join(td, "pwned")
        old_path = os.environ.get("PATH", "")
        old_fake = os.environ.get("FAKE_OUT")
        os.environ["PATH"] = bin_dir + os.pathsep + old_path
        os.environ["FAKE_OUT"] = pwn

        for bad in ["; touch " + pwn, "$(touch " + pwn + ")", "--json; touch " + pwn, "| touch " + pwn, "--help"]:
            try:
                src.run_export(bad)
                raise AssertionError(f"injection not rejected: {bad}")
            except ValueError:
                pass
        assert not os.path.exists(pwn), "injection executed!"
        score += 3

        # 合法参数仍可执行
        try:
            out = src.run_export("--json")
            assert out == "" or out is not None
            with open(pwn) as f:
                assert f.read().strip() == "OK --json"
        finally:
            if old_path is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = old_path
            if old_fake is None:
                os.environ.pop("FAKE_OUT", None)
            else:
                os.environ["FAKE_OUT"] = old_fake
        score += 1

        # 静态检查：无 shell 拼接，有路径校验
        if "shell=True" not in cand and ("realpath" in cand or "resolve" in cand):
            score += 1

    print(f"PASS  C6 score={score}/10")
    return 0


if __name__ == "__main__":
    sys.exit(main())
