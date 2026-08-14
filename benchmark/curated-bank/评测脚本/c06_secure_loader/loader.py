import os
import subprocess


def load_report(filename: str, base_dir: str = "reports") -> str:
    path = os.path.join(base_dir, filename)
    with open(path, encoding="utf-8") as f:
        return f.read()


def run_export(user_arg: str) -> str:
    return subprocess.run(
        "export_data " + user_arg, shell=True, capture_output=True, text=True
    ).stdout
