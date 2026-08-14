import json

from benchmark.agent_benchmark.high_pressure.grade import grade_response
from benchmark.agent_benchmark.high_pressure.models import Component, TaskCase


def sample_task() -> TaskCase:
    return TaskCase(
        id="T00",
        title="示例",
        prompt="示例题面",
        expected={"items": ["A", "B"], "count": 2, "status": "ok"},
        near_miss={"items": ["A"], "count": 1, "status": "ok"},
        components=(
            Component("items", 5),
            Component("count", 3),
            Component("status", 2),
        ),
    )


def test_grades_clean_json_as_full_pass():
    response = json.dumps(sample_task().expected, ensure_ascii=False)

    result = grade_response(sample_task(), response)

    assert result.points == 10
    assert result.whole_correct is True
    assert result.status == "correct"


def test_extracts_json_from_fence_and_explanation():
    response = '结论如下：\n```json\n{"items":["A","B"],"count":2,"status":"ok"}\n```'

    result = grade_response(sample_task(), response)

    assert result.points == 10
    assert result.format_compliant is False
    assert result.status == "correct"


def test_awards_component_points_for_partial_answer():
    response = '{"items":["A","B"],"count":1,"status":"ok"}'

    result = grade_response(sample_task(), response)

    assert result.points == 7
    assert result.whole_correct is False
    assert result.status == "partial"
    assert result.component_results == {
        "items": True,
        "count": False,
        "status": True,
    }


def test_classifies_missing_final_answer():
    result = grade_response(sample_task(), "我还需要继续枚举所有情况。")

    assert result.points == 0
    assert result.status == "unfinished"


def test_rejects_near_miss():
    response = json.dumps(sample_task().near_miss, ensure_ascii=False)

    result = grade_response(sample_task(), response)

    assert result.whole_correct is False
    assert result.points < 10
