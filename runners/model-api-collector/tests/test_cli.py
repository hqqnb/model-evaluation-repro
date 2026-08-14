from pathlib import Path

from model_api_collector.cli import main
from model_api_collector.runner import RunSummary


def write_inputs(tmp_path):
    config = tmp_path / "models.yaml"
    config.write_text(
        "models:\n"
        "  alpha:\n"
        "    model: provider/a\n"
        "  beta:\n"
        "    model: provider/b\n",
        encoding="utf-8",
    )
    prompts = tmp_path / "prompts.jsonl"
    prompts.write_text(
        '{"id":"p1","messages":[{"role":"user","content":"hello"}]}\n',
        encoding="utf-8",
    )
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ONEAPI_BASE_URL=http://localhost:9999\n"
        "ONEAPI_API_KEY=local-secret\n",
        encoding="utf-8",
    )
    return config, prompts, env_file


def test_validate_checks_inputs_without_running_requests(tmp_path, monkeypatch, capsys):
    config, prompts, env_file = write_inputs(tmp_path)

    def unexpected_run(**kwargs):
        raise AssertionError("validate must not execute requests")

    monkeypatch.setattr("model_api_collector.cli.run_evaluation", unexpected_run)

    exit_code = main(
        [
            "validate",
            "--config",
            str(config),
            "--prompts",
            str(prompts),
            "--env-file",
            str(env_file),
        ]
    )

    assert exit_code == 0
    assert "Models: 2" in capsys.readouterr().out


def test_preflight_constructs_payloads_without_running_requests(
    tmp_path, monkeypatch, capsys
):
    config, prompts, env_file = write_inputs(tmp_path)

    def unexpected_run(**kwargs):
        raise AssertionError("preflight must not execute requests")

    monkeypatch.setattr("model_api_collector.cli.run_evaluation", unexpected_run)

    exit_code = main(
        [
            "preflight",
            "--config",
            str(config),
            "--prompts",
            str(prompts),
            "--env-file",
            str(env_file),
            "--models",
            "all",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Preflight valid" in output
    assert "Models: 2" in output
    assert "Requests: 0" in output


def test_invalid_configuration_returns_two_without_traceback(
    tmp_path, capsys, monkeypatch
):
    config, prompts, env_file = write_inputs(tmp_path)
    monkeypatch.delenv("ONEAPI_API_KEY", raising=False)
    env_file.write_text("ONEAPI_BASE_URL=http://localhost:9999\n", encoding="utf-8")

    exit_code = main(
        [
            "validate",
            "--config",
            str(config),
            "--prompts",
            str(prompts),
            "--env-file",
            str(env_file),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "ONEAPI_API_KEY" in captured.err
    assert "Traceback" not in captured.err


def test_run_expands_all_models_and_returns_zero(tmp_path, monkeypatch, capsys):
    config, prompts, env_file = write_inputs(tmp_path)
    captured_args = {}
    run_path = tmp_path / "runs" / "run-success"

    def fake_run(**kwargs):
        captured_args.update(kwargs)
        return RunSummary(
            run_id="run-success",
            run_path=run_path,
            total=2,
            successful=2,
            failed=0,
        )

    monkeypatch.setattr("model_api_collector.cli.run_evaluation", fake_run)

    exit_code = main(
        [
            "run",
            "--config",
            str(config),
            "--prompts",
            str(prompts),
            "--env-file",
            str(env_file),
            "--models",
            "all",
            "--output",
            str(tmp_path / "runs"),
        ]
    )

    assert exit_code == 0
    assert captured_args["model_aliases"] == ["alpha", "beta"]
    assert captured_args["config_sha256"]
    assert captured_args["prompts_sha256"]
    assert captured_args["delivery_mode"] is None
    assert captured_args["max_attempts"] is None
    assert captured_args["repeat"] == 2
    assert str(run_path.resolve()) in capsys.readouterr().out


def test_run_allows_explicit_stream_mode_and_retry_limit(
    tmp_path, monkeypatch
):
    config, prompts, env_file = write_inputs(tmp_path)
    captured_args = {}

    def fake_run(**kwargs):
        captured_args.update(kwargs)
        return RunSummary(
            run_id="run-stream",
            run_path=tmp_path / "runs" / "run-stream",
            total=1,
            successful=1,
            failed=0,
        )

    monkeypatch.setattr("model_api_collector.cli.run_evaluation", fake_run)

    assert (
        main(
            [
                "run",
                "--config",
                str(config),
                "--prompts",
                str(prompts),
                "--env-file",
                str(env_file),
                "--models",
                "alpha",
                "--delivery-mode",
                "stream",
                "--max-attempts",
                "4",
            ]
        )
        == 0
    )
    assert captured_args["delivery_mode"] == "stream"
    assert captured_args["max_attempts"] == 4


def test_run_returns_one_when_any_request_fails(tmp_path, monkeypatch):
    config, prompts, env_file = write_inputs(tmp_path)

    monkeypatch.setattr(
        "model_api_collector.cli.run_evaluation",
        lambda **kwargs: RunSummary(
            run_id="run-failed",
            run_path=tmp_path / "runs" / "run-failed",
            total=2,
            successful=1,
            failed=1,
        ),
    )

    exit_code = main(
        [
            "run",
            "--config",
            str(config),
            "--prompts",
            str(prompts),
            "--env-file",
            str(env_file),
            "--models",
            "alpha",
        ]
    )

    assert exit_code == 1


def test_unknown_model_returns_two_before_run(tmp_path, monkeypatch, capsys):
    config, prompts, env_file = write_inputs(tmp_path)
    called = False

    def fake_run(**kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr("model_api_collector.cli.run_evaluation", fake_run)

    exit_code = main(
        [
            "run",
            "--config",
            str(config),
            "--prompts",
            str(prompts),
            "--env-file",
            str(env_file),
            "--models",
            "missing",
        ]
    )

    assert exit_code == 2
    assert called is False
    assert "Unknown model" in capsys.readouterr().err
