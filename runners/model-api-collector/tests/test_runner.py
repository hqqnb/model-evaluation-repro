import json

import pytest

from model_api_collector.config import ConfigError
from model_api_collector.models import ModelConfig, PromptCase, Settings
from model_api_collector.runner import run_evaluation
from model_api_collector.transport import TransportResult


def result(error_type=None):
    return TransportResult(
        started_at="2026-08-03T00:00:00Z",
        ended_at="2026-08-03T00:00:01Z",
        http_status=200 if error_type is None else 429,
        response_headers={"x-request-id": "fake"},
        content="answer" if error_type is None else "",
        reasoning="",
        finish_reason="stop" if error_type is None else None,
        usage={"total_tokens": 5} if error_type is None else None,
        time_to_headers_ms=1.0,
        time_to_first_event_ms=2.0 if error_type is None else None,
        time_to_first_reasoning_ms=None,
        time_to_first_text_ms=3.0 if error_type is None else None,
        total_time_ms=4.0,
        completed_stream=error_type is None,
        error_type=error_type,
        error_message="failed" if error_type else None,
        error_body=None,
    )


class FakeTransport:
    def __init__(self, results=None):
        self.calls = []
        self.results = list(results or [])

    def execute(self, endpoint, payload, raw_body_path):
        self.calls.append((endpoint, payload, raw_body_path))
        raw_body_path.write_text("raw", encoding="utf-8")
        return self.results.pop(0) if self.results else result()


def settings(parameters=None):
    return Settings(
        base_url="http://oneapi.example",
        api_key="secret",
        timeout_seconds=10,
        models={
            "alpha": ModelConfig(
                alias="alpha",
                model="provider/a",
                parameters=parameters or {"temperature": 0},
            ),
            "beta": ModelConfig(
                alias="beta",
                model="provider/b",
                stream=False,
                parameters={"temperature": 0},
            ),
        },
    )


def prompts():
    return [
        PromptCase(
            id="prompt-a",
            title="A",
            messages=[{"role": "user", "content": "A"}],
        ),
        PromptCase(
            id="prompt-b",
            title="B",
            messages=[{"role": "user", "content": "B"}],
        ),
    ]


def test_runner_executes_models_prompts_and_repeats_in_order(tmp_path):
    transport = FakeTransport()

    summary = run_evaluation(
        settings=settings(),
        model_aliases=["alpha", "beta"],
        prompt_cases=prompts(),
        repeat=2,
        output_root=tmp_path / "runs",
        config_sha256="config-hash",
        prompts_sha256="prompts-hash",
        transport=transport,
    )

    observed = [
        (
            call[1]["model"],
            call[1]["messages"][0]["content"],
            call[1]["stream"],
        )
        for call in transport.calls
    ]
    assert observed == [
        ("provider/a", "A", True),
        ("provider/a", "A", True),
        ("provider/a", "B", True),
        ("provider/a", "B", True),
        ("provider/b", "A", False),
        ("provider/b", "A", False),
        ("provider/b", "B", False),
        ("provider/b", "B", False),
    ]
    assert summary.total == 8
    assert summary.successful == 8
    assert summary.failed == 0
    run_metadata = json.loads((summary.run_path / "run.json").read_text())
    assert run_metadata["config_sha256"] == "config-hash"
    assert run_metadata["prompts_sha256"] == "prompts-hash"


def test_runner_continues_after_failure_without_retry(tmp_path):
    transport = FakeTransport([result("http_error"), result()])

    summary = run_evaluation(
        settings=settings(),
        model_aliases=["alpha"],
        prompt_cases=prompts()[:1],
        repeat=2,
        output_root=tmp_path / "runs",
        config_sha256="a",
        prompts_sha256="b",
        transport=transport,
    )

    assert len(transport.calls) == 2
    assert summary.successful == 1
    assert summary.failed == 1
    records = [
        json.loads(line)
        for line in (summary.run_path / "results.jsonl").read_text().splitlines()
    ]
    assert [record["status"] for record in records] == ["failed", "success"]


def test_runner_uses_input_for_responses_endpoint(tmp_path):
    transport = FakeTransport()
    response_settings = Settings(
        base_url="http://oneapi.example",
        api_key="secret",
        timeout_seconds=10,
        models={
            "opus-5": ModelConfig(
                alias="opus-5",
                model="Opus 5",
                endpoint="/v1/responses",
                parameters={
                    "temperature": 0,
                    "store": False,
                    "tools": [],
                },
            )
        },
    )

    run_evaluation(
        settings=response_settings,
        model_aliases=["opus-5"],
        prompt_cases=prompts()[:1],
        repeat=1,
        output_root=tmp_path / "runs",
        config_sha256="a",
        prompts_sha256="b",
        transport=transport,
    )

    payload = transport.calls[0][1]
    assert payload == {
        "model": "Opus 5",
        "input": [{"role": "user", "content": "A"}],
        "stream": True,
        "temperature": 0,
        "store": False,
        "tools": [],
    }
    assert "messages" not in payload


@pytest.mark.parametrize("reserved", ["model", "messages", "input", "stream"])
def test_runner_rejects_reserved_model_parameters_before_network(
    tmp_path, reserved
):
    transport = FakeTransport()
    bad_settings = settings({reserved: "override"})

    with pytest.raises(ConfigError, match="reserved"):
        run_evaluation(
            settings=bad_settings,
            model_aliases=["alpha"],
            prompt_cases=prompts()[:1],
            repeat=1,
            output_root=tmp_path / "runs",
            config_sha256="a",
            prompts_sha256="b",
            transport=transport,
        )

    assert transport.calls == []
    assert not (tmp_path / "runs").exists()


def test_runner_rejects_unknown_model_before_network(tmp_path):
    transport = FakeTransport()

    with pytest.raises(ConfigError, match="Unknown model"):
        run_evaluation(
            settings=settings(),
            model_aliases=["missing"],
            prompt_cases=prompts()[:1],
            repeat=1,
            output_root=tmp_path / "runs",
            config_sha256="a",
            prompts_sha256="b",
            transport=transport,
        )

    assert transport.calls == []
