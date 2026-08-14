from pathlib import Path


def test_rendered_short_logic_artifacts_exist_and_are_consistent():
    from benchmark.agent_benchmark.short_logic.render import render_all

    paths = render_all()
    assert all(Path(path).exists() for path in paths.values())
    assert set(paths) == {"markdown", "answer_key", "prompts"}
