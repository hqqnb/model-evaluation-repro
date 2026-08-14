import json

from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.short_logic.grade import grade_response
from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.short_logic.tasks import build_tasks


def _task(task_id):
    return next(task for task in build_tasks() if task.id == task_id)


def test_s04_accepts_numeric_sentence_ids_as_semantically_equivalent():
    response = json.dumps(
        {
            "solutions": ["FFTFTF"],
            "count": 1,
            "always_true": [3, 5],
            "always_false": [1, 2, 4, 6],
        }
    )

    result = grade_response(_task("S04"), response)

    assert result.points == 10
    assert result.whole_correct is True


def test_s05_accepts_equivalent_counterexample_field_names():
    base = _task("S05").expected
    for field in ("state", "n", "failing_state"):
        answer = dict(base)
        answer["fast_action_counterexample"] = {
            "action": "parity_even_then_guess0",
            field: 2,
        }

        result = grade_response(_task("S05"), json.dumps(answer))

        assert result.points == 10
        assert result.whole_correct is True


def test_semantic_normalization_does_not_accept_wrong_values():
    answer = dict(_task("S05").expected)
    answer["fast_action_counterexample"] = {
        "action": "parity_even_then_guess0",
        "state": 1,
    }

    result = grade_response(_task("S05"), json.dumps(answer))

    assert result.points == 9
    assert result.whole_correct is False
