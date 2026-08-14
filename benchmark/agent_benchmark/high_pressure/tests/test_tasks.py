from benchmark.agent_benchmark.high_pressure.grade import grade_response
from benchmark.agent_benchmark.high_pressure.tasks import build_tasks


def test_builds_ten_valid_tasks():
    tasks = build_tasks()

    assert [task.id for task in tasks] == [f"T{index:02d}" for index in range(1, 11)]
    assert sum(sum(component.points for component in task.components) for task in tasks) == 100
    assert all(len(task.prompt) >= 500 for task in tasks)
    assert all(len(task.components) >= 3 for task in tasks)


def test_expected_answers_pass_and_near_misses_fail():
    for task in build_tasks():
        expected_result = grade_response(task, __import__("json").dumps(task.expected))
        near_miss_result = grade_response(task, __import__("json").dumps(task.near_miss))

        assert expected_result.whole_correct, task.id
        assert expected_result.points == 10, task.id
        assert not near_miss_result.whole_correct, task.id


def test_task_answers_are_deterministic():
    first = build_tasks()
    second = build_tasks()

    assert [task.expected for task in first] == [task.expected for task in second]


def test_game_task_includes_both_jump_captures():
    task = {task.id: task for task in build_tasks()}["T03"]

    assert task.expected["Q_legal_moves"] == [
        "b2>a2",
        "b2>b1",
        "b2>b4",
        "b2>d2",
    ]


def test_pipe_task_uses_declared_action_order_for_ties():
    task = {task.id: task for task in build_tasks()}["T09"]

    assert task.expected["sequence"] == [
        "关闭进水",
        "打开旁路",
        "排空",
        "拆滤网",
        "投化学剂",
        "准备泵",
        "反冲B",
        "装滤网",
        "关闭旁路",
        "打开进水",
    ]


def test_machine_check_number_is_observational_not_scored():
    task = {task.id: task for task in build_tasks()}["T05"]

    assert "first_danger_check" not in {
        component.field for component in task.components
    }
    assert sum(component.points for component in task.components) == 10
