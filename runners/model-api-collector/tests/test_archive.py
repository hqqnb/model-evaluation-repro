import csv
import json

from model_api_collector.archive import RunArchive


def test_archive_writes_request_records_and_summaries(tmp_path):
    archive = RunArchive.create(
        root=tmp_path / "runs",
        run_metadata={
            "run_id": "run-001",
            "config_sha256": "config-hash",
            "prompts_sha256": "prompts-hash",
        },
        api_key="test-secret",
    )
    success_dir = archive.start_request(
        "req-success",
        {
            "model": "model-a",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": True,
        },
    )
    (success_dir / "response.sse").write_text("data: [DONE]\n\n")
    archive.finish_request(
        "req-success",
        response_headers={"x-request-id": "abc"},
        content="answer",
        reasoning="",
        metadata={
            "prompt_id": "prompt-a",
            "model_alias": "alpha",
            "model": "model-a",
            "status": "success",
            "http_status": 200,
            "total_time_ms": 42.5,
            "time_to_first_event_ms": 10.0,
            "time_to_first_reasoning_ms": 15.0,
            "time_to_first_text_ms": 20.0,
            "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            "raw_response_path": "requests/req-success/response.sse",
        },
    )

    error_dir = archive.start_request(
        "req-error",
        {
            "model": "model-b",
            "messages": [{"role": "user", "content": "test-secret must be redacted"}],
            "stream": False,
        },
    )
    (error_dir / "response.json").write_text('{"error":"failed"}')
    archive.finish_request(
        "req-error",
        response_headers={},
        content="",
        reasoning="",
        metadata={
            "prompt_id": "prompt-a",
            "model_alias": "beta",
            "model": "model-b",
            "status": "failed",
            "http_status": 429,
            "total_time_ms": 15.0,
            "time_to_first_event_ms": None,
            "time_to_first_reasoning_ms": None,
            "time_to_first_text_ms": None,
            "usage": None,
            "raw_response_path": "requests/req-error/response.json",
        },
        error={
            "type": "http_error",
            "message": "Authorization test-secret failed",
            "body": "test-secret",
        },
    )
    archive.finalize()

    request = json.loads((success_dir / "request.json").read_text())
    metadata = json.loads((success_dir / "metadata.json").read_text())
    assert request["messages"][0]["content"] == "hello"
    assert metadata["status"] == "success"
    assert len(metadata["request_sha256"]) == 64
    assert (success_dir / "response.md").read_text() == "answer"
    assert not (success_dir / "error.json").exists()

    error_request = (error_dir / "request.json").read_text()
    error_json = (error_dir / "error.json").read_text()
    assert "test-secret" not in error_request
    assert "test-secret" not in error_json
    assert "[REDACTED]" in error_json

    results = [
        json.loads(line)
        for line in (archive.run_path / "results.jsonl").read_text().splitlines()
    ]
    assert len(results) == 2
    assert results[0]["request_id"] == "req-success"
    assert results[1]["error_type"] == "http_error"

    with (archive.run_path / "summary.csv").open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))
    assert len(rows) == 2
    assert rows[0]["total_tokens"] == "5"
    assert rows[0]["time_to_first_reasoning_ms"] == "15.0"
    assert rows[1]["status"] == "failed"


def test_json_files_are_written_atomically_without_temp_files(tmp_path):
    archive = RunArchive.create(
        root=tmp_path,
        run_metadata={"run_id": "run-atomic"},
        api_key="secret",
    )
    archive.start_request(
        "req-1",
        {"model": "a", "messages": [{"role": "user", "content": "x"}]},
    )

    assert not list(archive.run_path.rglob("*.tmp"))
