import json

import pytest

import model_api_collector.sse as sse
from model_api_collector.sse import (
    SSEDecoder,
    SSEParseError,
    extract_chat_delta,
)


def test_decoder_handles_fragmented_utf8_and_json():
    decoder = SSEDecoder()
    encoded = "你".encode("utf-8")
    events = []
    events.extend(decoder.feed(b'data: {"choices":[{"delta":{"content":"'))
    events.extend(decoder.feed(encoded[:1]))
    events.extend(decoder.feed(encoded[1:] + b'"}}]}\n\n'))

    assert events == ['{"choices":[{"delta":{"content":"你"}}]}']


def test_decoder_supports_crlf_comments_and_multiline_data():
    decoder = SSEDecoder()

    events = decoder.feed(
        b": keepalive\r\n\r\ndata: first\r\ndata: second\r\n\r\n"
    )

    assert events == ["first\nsecond"]


def test_decoder_flushes_terminal_event_at_eof_without_blank_line():
    decoder = SSEDecoder()

    assert decoder.feed(b"data: [DONE]\n") == []
    assert decoder.finish() == ["[DONE]"]
    assert decoder.finish() == []


def test_extract_chat_delta_collects_content_reasoning_usage_and_finish():
    payload = json.dumps(
        {
            "choices": [
                {
                    "delta": {
                        "content": "answer",
                        "reasoning_content": "thought",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        }
    )

    delta = extract_chat_delta(payload)

    assert delta.content == "answer"
    assert delta.reasoning == "thought"
    assert delta.finish_reason == "stop"
    assert delta.usage == {"prompt_tokens": 3, "completion_tokens": 2}
    assert delta.done is False


def test_extract_chat_delta_handles_done_and_empty_choices():
    assert extract_chat_delta("[DONE]").done is True
    empty = extract_chat_delta('{"choices":[],"usage":{"total_tokens":5}}')
    assert empty.content == ""
    assert empty.usage == {"total_tokens": 5}


def test_extract_chat_delta_rejects_invalid_json():
    with pytest.raises(SSEParseError, match="Invalid SSE JSON"):
        extract_chat_delta("{broken")


def test_extract_responses_delta_collects_visible_text():
    delta = sse.extract_responses_delta(
        json.dumps(
            {
                "type": "response.output_text.delta",
                "delta": "hello",
            }
        )
    )

    assert delta.content == "hello"
    assert delta.done is False


def test_extract_responses_delta_collects_reasoning_summary():
    delta = sse.extract_responses_delta(
        json.dumps(
            {
                "type": "response.reasoning_summary_text.delta",
                "delta": "thought",
            }
        )
    )

    assert delta.reasoning == "thought"


def test_extract_responses_delta_completes_and_normalizes_usage():
    delta = sse.extract_responses_delta(
        json.dumps(
            {
                "type": "response.completed",
                "response": {
                    "status": "completed",
                    "usage": {
                        "input_tokens": 6,
                        "output_tokens": 2,
                        "total_tokens": 8,
                    },
                },
            }
        )
    )

    assert delta.done is True
    assert delta.finish_reason == "stop"
    assert delta.usage == {
        "input_tokens": 6,
        "output_tokens": 2,
        "total_tokens": 8,
        "prompt_tokens": 6,
        "completion_tokens": 2,
    }
    assert delta.response_metadata == {
        "model": None,
        "status": "completed",
        "temperature": None,
        "top_p": None,
        "reasoning": None,
        "tools": None,
    }


def test_extract_responses_delta_collects_effective_parameters():
    delta = sse.extract_responses_delta(
        json.dumps(
            {
                "type": "response.created",
                "response": {
                    "model": "claude-opus-5",
                    "status": "in_progress",
                    "temperature": 1,
                    "top_p": 1,
                    "reasoning": None,
                    "tools": [],
                },
            }
        )
    )

    assert delta.response_metadata == {
        "model": "claude-opus-5",
        "status": "in_progress",
        "temperature": 1,
        "top_p": 1,
        "reasoning": None,
        "tools": [],
    }


def test_extract_responses_delta_rejects_failed_events():
    with pytest.raises(SSEParseError, match="Responses API failed"):
        sse.extract_responses_delta(
            json.dumps(
                {
                    "type": "response.failed",
                    "response": {
                        "error": {
                            "message": "provider failed",
                        }
                    },
                }
            )
        )


def test_extract_responses_delta_rejects_invalid_json():
    with pytest.raises(SSEParseError, match="Invalid Responses SSE JSON"):
        sse.extract_responses_delta("{broken")
