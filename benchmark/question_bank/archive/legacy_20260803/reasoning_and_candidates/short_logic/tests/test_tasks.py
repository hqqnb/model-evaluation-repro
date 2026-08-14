from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.high_pressure.grade import grade_response
from benchmark.question_bank.archive.legacy_20260803.reasoning_and_candidates.short_logic.tasks import build_tasks


def test_short_logic_bank_has_six_short_deterministic_tasks():
    tasks = build_tasks()

    assert [task.id for task in tasks] == [f"S{i:02d}" for i in range(1, 7)]
    assert all(300 <= len(task.prompt) <= 900 for task in tasks)
    assert all(sum(component.points for component in task.components) == 10 for task in tasks)
    assert all(4 <= len(task.components) <= 6 for task in tasks)
    assert all(task.expected == build_tasks()[index].expected for index, task in enumerate(tasks))


def test_every_near_miss_loses_at_least_one_scored_component():
    for task in build_tasks():
        response = __import__("json").dumps(task.near_miss, ensure_ascii=False)
        result = grade_response(task, response)
        assert not result.whole_correct, task.id


def test_every_scored_component_exists_in_the_expected_answer():
    for task in build_tasks():
        missing = [
            component.field
            for component in task.components
            if component.field not in task.expected
        ]
        assert missing == [], f"{task.id}: {missing}"


def test_prompts_do_not_embed_answer_values_as_output_examples():
    tasks = {task.id: task for task in build_tasks()}
    forbidden = {
        "S01": ['"C_or_D":"necessary"', '"world_count":3'],
        "S02": ['"repair_size":2', '"color":"green"'],
        "S03": ['"steps":5', '"lower_bound":5'],
        "S04": ["FFTFTF"],
        "S05": ['"first_action":"parity"', '"guaranteed_win":true'],
        "S06": ['"D":1,"E":0,"F":1,"G":0,"H":1'],
    }

    for task_id, snippets in forbidden.items():
        for snippet in snippets:
            assert snippet not in tasks[task_id].prompt, f"{task_id}: {snippet}"


def test_prompts_define_deterministic_choices_for_equivalent_answers():
    tasks = {task.id: task for task in build_tasks()}

    assert "字典序最小" in tasks["S01"].prompt
    assert "问题优先级" in tasks["S05"].prompt
    assert "只比较两次干预结果" in tasks["S06"].prompt
