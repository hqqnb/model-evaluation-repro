import os
import subprocess


ALLOWED_ARGS = {"--json", "--csv", "--quiet"}


def load_report(filename: str, base_dir: str = "reports") -> str:
    if os.path.isabs(filename):
        raise ValueError("absolute path is not allowed")
    base = os.path.realpath(base_dir)
    target = os.path.realpath(os.path.join(base, filename))
    if target != base and not target.startswith(base + os.sep):
        raise ValueError("path escapes base directory")
    if not os.path.isfile(target):
        raise ValueError("not a regular file")
    with open(target, encoding="utf-8") as f:
        return f.read()


def run_export(user_arg: str) -> str:
    if user_arg not in ALLOWED_ARGS:
        raise ValueError(f"argument not allowed: {user_arg!r}")
    return subprocess.run(
        ["export_data", user_arg], capture_output=True, text=True, check=True
    ).stdout
