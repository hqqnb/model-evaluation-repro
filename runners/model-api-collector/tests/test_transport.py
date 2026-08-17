import json

from model_api_collector.transport import OneAPITransport


def make_transport(
    fake_server, timeout=2, max_attempts=3, complete_timeout=None
):
    return OneAPITransport(
        base_url=fake_server.url,
        api_key="test-secret",
        timeout_seconds=timeout,
        max_attempts=max_attempts,
        complete_timeout_seconds=complete_timeout,
    )


def test_streaming_request_is_archived_and_timed(tmp_path, fake_server):
    payload = {
        "model": "provider/model-a",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": True,
        "temperature": 0,
    }
    raw_path = tmp_path / "response.sse"

    result = make_transport(fake_server).execute(
        endpoint="/v1/chat/completions",
        payload=payload,
        raw_body_path=raw_path,
    )

    assert fake_server.requests[0]["json"] == payload
    assert fake_server.requests[0]["headers"]["Authorization"] == "Bearer test-secret"
    assert result.content == "你好"
    assert result.reasoning == ""
    assert result.http_status == 200
    assert result.response_headers["x-request-id"] == "fake-request"
    assert result.usage == {"prompt_tokens": 3, "completion_tokens": 2}
    assert result.finish_reason == "stop"
    assert result.completed_stream is True
    assert result.error_type is None
    assert result.time_to_headers_ms >= 0
    assert result.time_to_first_event_ms >= result.time_to_headers_ms
    assert result.time_to_first_text_ms >= result.time_to_first_event_ms
    assert result.total_time_ms >= result.time_to_first_text_ms
    assert b"data: [DONE]" in raw_path.read_bytes()


def test_non_streaming_response_is_preserved_and_extracted(tmp_path, fake_server):
    raw_path = tmp_path / "response.json"

    result = make_transport(fake_server).execute(
        endpoint="/v1/chat/completions-json",
        payload={
            "model": "provider/model-a",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
        raw_body_path=raw_path,
    )

    assert json.loads(raw_path.read_text())["choices"][0]["message"]["content"] == "normal answer"
    assert result.content == "normal answer"
    assert result.finish_reason == "stop"
    assert result.usage == {"prompt_tokens": 2, "completion_tokens": 2}
    assert result.time_to_first_event_ms is None
    assert result.time_to_first_text_ms is None
    assert result.error_type is None


def test_responses_stream_completes_without_done_event(tmp_path, fake_server):
    payload = {
        "model": "Opus 5",
        "input": [{"role": "user", "content": "hello"}],
        "stream": True,
        "temperature": 0,
        "store": False,
        "tools": [],
    }
    raw_path = tmp_path / "response.sse"

    result = make_transport(fake_server).execute(
        endpoint="/v1/responses",
        payload=payload,
        raw_body_path=raw_path,
    )

    assert fake_server.requests[0]["json"] == payload
    assert result.content == "hello"
    assert result.finish_reason == "stop"
    assert result.completed_stream is True
    assert result.usage == {
        "input_tokens": 6,
        "output_tokens": 1,
        "total_tokens": 7,
        "prompt_tokens": 6,
        "completion_tokens": 1,
    }
    assert result.time_to_first_event_ms >= result.time_to_headers_ms
    assert result.time_to_first_text_ms >= result.time_to_first_event_ms
    assert result.error_type is None
    assert b"response.completed" in raw_path.read_bytes()
    assert b"[DONE]" not in raw_path.read_bytes()


def test_non_streaming_responses_output_is_extracted(tmp_path, fake_server):
    raw_path = tmp_path / "response.json"

    result = make_transport(fake_server).execute(
        endpoint="/v1/responses",
        payload={
            "model": "Opus 5",
            "input": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
        raw_body_path=raw_path,
    )

    assert result.content == "normal response"
    assert result.finish_reason == "stop"
    assert result.usage == {
        "input_tokens": 4,
        "output_tokens": 2,
        "total_tokens": 6,
        "prompt_tokens": 4,
        "completion_tokens": 2,
    }
    assert result.error_type is None


def test_incomplete_non_streaming_responses_is_not_successful(tmp_path, fake_server):
    result = make_transport(fake_server, max_attempts=1).execute(
        endpoint="/v1/responses-incomplete-json",
        payload={
            "model": "Opus 5",
            "input": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
        raw_body_path=tmp_path / "response.json",
    )

    assert result.content == ""
    assert result.succeeded is False
    assert result.error_type == "incomplete_response"
    assert result.attempt_count == 1


def test_retry_selects_complete_response_and_preserves_attempts(
    tmp_path, fake_server
):
    raw_path = tmp_path / "response.json"
    result = make_transport(fake_server).execute(
        endpoint="/retry-once",
        payload={
            "model": "provider/model-a",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
        raw_body_path=raw_path,
    )

    assert result.succeeded is True
    assert result.content == "recovered answer"
    assert result.attempt_count == 2
    assert result.attempt_errors == [
        {"type": "http_error", "message": "OneAPI returned HTTP 503"}
    ]
    assert (tmp_path / "response.attempt-1.json").exists()


def test_transient_upstream_404_is_retried(tmp_path, fake_server):
    raw_path = tmp_path / "response.json"
    result = make_transport(fake_server).execute(
        endpoint="/upstream-404-once",
        payload={
            "model": "Opus 5",
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
        raw_body_path=raw_path,
    )

    assert result.succeeded is True
    assert result.content == "recovered upstream answer"
    assert result.attempt_count == 2
    assert result.attempt_errors == [
        {"type": "http_error", "message": "OneAPI returned HTTP 404"}
    ]
    assert (tmp_path / "response.attempt-1.json").exists()


def test_responses_stream_preserves_effective_parameters(tmp_path, fake_server):
    result = make_transport(fake_server, max_attempts=1).execute(
        endpoint="/v1/responses-effective-stream",
        payload={
            "model": "Opus 5",
            "input": [{"role": "user", "content": "hello"}],
            "stream": True,
            "temperature": 0,
            "reasoning_effort": "max",
            "tools": [],
        },
        raw_body_path=tmp_path / "response.sse",
    )

    assert result.succeeded is True
    assert result.content == "effective answer"
    assert result.response_metadata == {
        "model": "claude-opus-5",
        "status": "completed",
        "temperature": 1,
        "top_p": 1,
        "reasoning": None,
        "tools": [],
    }


def test_deterministic_conversion_error_is_not_retried(tmp_path, fake_server):
    result = make_transport(fake_server).execute(
        endpoint="/convert-not-implemented",
        payload={
            "model": "Opus 5",
            "input": [{"role": "user", "content": "hello"}],
            "stream": False,
        },
        raw_body_path=tmp_path / "response.json",
    )

    assert result.succeeded is False
    assert result.error_type == "http_error"
    assert result.attempt_count == 1
    assert len(fake_server.requests) == 1


def test_http_error_retains_status_and_body(tmp_path, fake_server):
    result = make_transport(fake_server).execute(
        endpoint="/status/429",
        payload={"model": "a", "messages": [], "stream": True},
        raw_body_path=tmp_path / "response.sse",
    )

    assert result.http_status == 429
    assert result.error_type == "http_error"
    assert "rate limited" in result.error_body
    assert "test-secret" not in result.error_message


def test_invalid_sse_retains_raw_body(tmp_path, fake_server):
    raw_path = tmp_path / "response.sse"

    result = make_transport(fake_server).execute(
        endpoint="/invalid-sse",
        payload={"model": "a", "messages": [], "stream": True},
        raw_body_path=raw_path,
    )

    assert result.error_type == "stream_parse_error"
    assert raw_path.read_bytes() == b"data: {broken\n\n"


def test_incomplete_stream_retains_partial_text(tmp_path, fake_server):
    result = make_transport(fake_server).execute(
        endpoint="/broken-stream",
        payload={"model": "a", "messages": [], "stream": True},
        raw_body_path=tmp_path / "response.sse",
    )

    assert result.content == "partial"
    assert result.completed_stream is False
    assert result.error_type == "incomplete_stream"


def test_stream_accepts_done_event_terminated_by_eof(tmp_path, fake_server):
    result = make_transport(fake_server).execute(
        endpoint="/eof-done",
        payload={"model": "a", "messages": [], "stream": True},
        raw_body_path=tmp_path / "response.sse",
    )

    assert result.content == "complete"
    assert result.finish_reason == "stop"
    assert result.completed_stream is True
    assert result.error_type is None


def test_reasoning_is_timed_separately_from_visible_text(tmp_path, fake_server):
    result = make_transport(fake_server).execute(
        endpoint="/reasoning-first",
        payload={"model": "a", "messages": [], "stream": True},
        raw_body_path=tmp_path / "response.sse",
    )

    assert result.reasoning == "thought"
    assert result.content == "answer"
    assert result.time_to_first_reasoning_ms >= result.time_to_first_event_ms
    assert result.time_to_first_text_ms > result.time_to_first_reasoning_ms


def test_stream_with_done_but_without_finish_reason_is_incomplete(
    tmp_path, fake_server
):
    result = make_transport(fake_server, max_attempts=1).execute(
        endpoint="/done-without-finish",
        payload={"model": "a", "messages": [], "stream": True},
        raw_body_path=tmp_path / "response.sse",
    )

    assert result.content == "partial"
    assert result.completed_stream is True
    assert result.error_type == "incomplete_stream"


def test_responses_completed_event_must_report_completed_status(
    tmp_path, fake_server
):
    result = make_transport(fake_server, max_attempts=1).execute(
        endpoint="/responses-incomplete-completed",
        payload={"model": "Opus 5", "input": [], "stream": True},
        raw_body_path=tmp_path / "response.sse",
    )

    assert result.content == "partial"
    assert result.error_type == "stream_parse_error"


def test_timeout_is_classified_without_leaking_key(tmp_path, fake_server):
    result = make_transport(fake_server, timeout=0.05).execute(
        endpoint="/slow",
        payload={"model": "a", "messages": [], "stream": False},
        raw_body_path=tmp_path / "response.json",
    )

    assert result.error_type == "timeout"
    assert result.http_status is None
    assert "test-secret" not in result.error_message


def test_non_streaming_uses_the_separate_complete_timeout(tmp_path, fake_server):
    result = make_transport(
        fake_server,
        timeout=0.05,
        complete_timeout=0.5,
        max_attempts=1,
    ).execute(
        endpoint="/slow",
        payload={"model": "a", "messages": [], "stream": False},
        raw_body_path=tmp_path / "response.json",
    )

    assert result.error_type == "response_parse_error"
