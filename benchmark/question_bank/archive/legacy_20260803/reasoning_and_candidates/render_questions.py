from pathlib import Path

from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.grade import load_questions


OUTPUT = Path(__file__).resolve().parent / "QUESTIONS.md"


def render() -> str:
    lines = [
        "# 模型推理能力候选题库",
        "",
        "每题 5 分，共 100 分。除题目另有说明外，答案应放在统一输出对象的 `answer` 字段中。",
        "",
    ]
    for item in load_questions():
        lines.extend(
            [
                f"## {item['id']}",
                "",
                f"难度：{item['difficulty']}",
                "",
                item["prompt"],
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


if __name__ == "__main__":
    OUTPUT.write_text(render(), encoding="utf-8")
    print(OUTPUT)
