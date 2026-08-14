"""Structural checks for the reviewer-facing multimodal benchmark bank."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
TASKS = ROOT / "MULTIMODAL_TASKS.md"
TASK_IDS = ["M01", "M02", "M03", "M04"]
REQUIRED_HEADINGS = ["给模型的题面", "标准答案", "计分项", "严重失败规则", "人类证据卡"]
ASSETS = [
    "assets/multimodal/m01-star-hidden-question.svg",
    "assets/multimodal/m02-pattern-matrix.svg",
    "assets/multimodal/m03-viral-contrast-card.svg",
    "assets/multimodal/m04-multi-panel-anomaly.svg",
]


def task_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"^## (M0[1-4]) .+$", text, re.MULTILINE))
    sections = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = text[match.start():end]
    return sections


def score_total(section: str) -> int:
    total = 0
    for row in re.findall(r"^\| M\d{2}-\d+ \| .+ \| (\d+) \|$", section, re.MULTILINE):
        total += int(row)
    return total


def main() -> None:
    text = TASKS.read_text(encoding="utf-8")
    sections = task_sections(text)
    assert list(sections) == TASK_IDS, f"expected tasks {TASK_IDS}, found {list(sections)}"

    for task_id, section in sections.items():
        for heading in REQUIRED_HEADINGS:
            assert f"### {heading}" in section, f"{task_id} missing heading: {heading}"
        total = score_total(section)
        assert total == 100, f"{task_id} score total is {total}"

    for asset in ASSETS:
        path = ROOT / asset
        assert path.exists(), f"missing asset: {asset}"
        assert path.stat().st_size > 100, f"asset is unexpectedly small: {asset}"

    print("Validated 4 multimodal tasks; each totals 100 points; all local assets exist.")


if __name__ == "__main__":
    main()
