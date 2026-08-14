import json

from model_api_collector.cli import main


def test_cli_collects_a_complete_streamed_run(tmp_path, fake_server):
    config = tmp_path / "models.yaml"
    config.write_text(
        "models:\n"
        "  alpha:\n"
        "    model: provider/a\n"
        "    parameters:\n"
        "      temperature: 0\n",
        encoding="utf-8",
    )
    prompts = tmp_path / "prompts.jsonl"
    prompts.write_text(
        '{"id":"smoke-001","messages":[{"role":"user","content":"hello"}]}\n',
        encoding="utf-8",
    )
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"ONEAPI_BASE_URL={fake_server.url}\nONEAPI_API_KEY=e2e-secret\n",
        encoding="utf-8",
    )
    output = tmp_path / "runs"

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
            "--delivery-mode",
            "stream",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    run_path = next(output.iterdir())
    assert len(list((run_path / "requests").iterdir())) == 2
    records = [
        json.loads(line)
        for line in (run_path / "results.jsonl").read_text().splitlines()
    ]
    assert len(records) == 2
    assert {record["prompt_id"] for record in records} == {"smoke-001"}
    assert len({record["request_id"] for record in records}) == 2
    request_path = next((run_path / "requests").iterdir())
    request = json.loads((request_path / "request.json").read_text())
    metadata = json.loads((request_path / "metadata.json").read_text())
    assert request == {
        "model": "provider/a",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": True,
        "temperature": 0,
    }
    assert (request_path / "response.md").read_text() == "你好"
    assert b"data: [DONE]" in (request_path / "response.sse").read_bytes()
    assert metadata["status"] == "success"
    assert metadata["time_to_first_reasoning_ms"] is None
    assert metadata["time_to_first_text_ms"] >= 0
    assert "e2e-secret" not in json.dumps(metadata)
    assert (run_path / "results.jsonl").read_text().strip()
    assert (run_path / "summary.csv").read_text().strip()


def test_cli_collects_a_complete_responses_run(tmp_path, fake_server):
    config = tmp_path / "models.yaml"
    config.write_text(
        "models:\n"
        "  opus-5:\n"
        "    model: Opus 5\n"
        "    endpoint: /v1/responses\n"
        "    parameters:\n"
        "      temperature: 0\n"
        "      store: false\n"
        "      tools: []\n",
        encoding="utf-8",
    )
    prompts = tmp_path / "prompts.jsonl"
    prompts.write_text(
        '{"id":"smoke-002","messages":[{"role":"user","content":"hello"}]}\n',
        encoding="utf-8",
    )
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"ONEAPI_BASE_URL={fake_server.url}\nONEAPI_API_KEY=e2e-secret\n",
        encoding="utf-8",
    )
    output = tmp_path / "runs"

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
            "opus-5",
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    run_path = next(output.iterdir())
    assert len(list((run_path / "requests").iterdir())) == 2
    assert len((run_path / "results.jsonl").read_text().splitlines()) == 2
    request_path = next((run_path / "requests").iterdir())
    request = json.loads((request_path / "request.json").read_text())
    metadata = json.loads((request_path / "metadata.json").read_text())
    assert request == {
        "model": "Opus 5",
        "input": [{"role": "user", "content": "hello"}],
        "stream": False,
        "temperature": 0,
        "store": False,
        "tools": [],
    }
    assert (request_path / "response.md").read_text() == "normal response"
    assert metadata["status"] == "success"
    assert metadata["completed_stream"] is False
    assert metadata["usage"]["prompt_tokens"] == 4
    assert metadata["usage"]["completion_tokens"] == 2
    assert metadata["requested_parameters"] == {
        "temperature": 0,
        "store": False,
        "tools": [],
    }
    assert metadata["effective_parameters"] == {
        "model": "Opus 5",
        "status": "completed",
        "temperature": None,
        "top_p": None,
        "reasoning": None,
        "tools": None,
    }
