import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


class SSEParseError(ValueError):
    pass


class SSEDecoder:
    def __init__(self) -> None:
        self._buffer = bytearray()

    def feed(self, chunk: bytes) -> List[str]:
        self._buffer.extend(chunk)
        payloads: List[str] = []
        while True:
            separator = self._find_separator()
            if separator is None:
                break
            index, length = separator
            event_bytes = bytes(self._buffer[:index])
            del self._buffer[: index + length]
            payload = self._parse_event(event_bytes)
            if payload is not None:
                payloads.append(payload)
        return payloads

    def finish(self) -> List[str]:
        if not self._buffer:
            return []
        event_bytes = bytes(self._buffer)
        self._buffer.clear()
        payload = self._parse_event(event_bytes)
        return [payload] if payload is not None else []

    def _find_separator(self) -> Optional[Tuple[int, int]]:
        candidates = []
        for separator in (b"\r\n\r\n", b"\n\n"):
            index = self._buffer.find(separator)
            if index >= 0:
                candidates.append((index, len(separator)))
        return min(candidates) if candidates else None

    @staticmethod
    def _parse_event(event_bytes: bytes) -> Optional[str]:
        try:
            event = event_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SSEParseError(f"Invalid UTF-8 in SSE event: {exc}") from exc
        data_lines = []
        for line in event.replace("\r\n", "\n").split("\n"):
            if not line or line.startswith(":"):
                continue
            if line == "data":
                data_lines.append("")
            elif line.startswith("data:"):
                value = line[5:]
                if value.startswith(" "):
                    value = value[1:]
                data_lines.append(value)
        if not data_lines:
            return None
        return "\n".join(data_lines)


@dataclass(frozen=True)
class ChatDelta:
    content: str = ""
    reasoning: str = ""
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    response_metadata: Optional[Dict[str, Any]] = None
    done: bool = False


def _response_metadata(response: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "model": response.get("model"),
        "status": response.get("status"),
        "temperature": response.get("temperature"),
        "top_p": response.get("top_p"),
        "reasoning": response.get("reasoning"),
        "tools": response.get("tools"),
    }


def extract_chat_delta(payload: str) -> ChatDelta:
    if payload.strip() == "[DONE]":
        return ChatDelta(done=True)
    try:
        item = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SSEParseError(f"Invalid SSE JSON: {exc}") from exc
    if not isinstance(item, dict):
        raise SSEParseError("Invalid SSE JSON: top-level value must be an object")

    usage = item.get("usage")
    if not isinstance(usage, dict):
        usage = None
    choices = item.get("choices")
    if not isinstance(choices, list) or not choices:
        return ChatDelta(usage=usage)

    choice = choices[0] if isinstance(choices[0], dict) else {}
    delta = choice.get("delta")
    if not isinstance(delta, dict):
        delta = {}
    content = delta.get("content")
    reasoning = delta.get("reasoning_content")
    finish_reason = choice.get("finish_reason")
    return ChatDelta(
        content=content if isinstance(content, str) else "",
        reasoning=reasoning if isinstance(reasoning, str) else "",
        finish_reason=finish_reason if isinstance(finish_reason, str) else None,
        usage=usage,
    )


def extract_responses_delta(payload: str) -> ChatDelta:
    if payload.strip() == "[DONE]":
        return ChatDelta(done=True)
    try:
        item = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SSEParseError(f"Invalid Responses SSE JSON: {exc}") from exc
    if not isinstance(item, dict):
        raise SSEParseError(
            "Invalid Responses SSE JSON: top-level value must be an object"
        )

    event_type = item.get("type")
    if event_type == "response.output_text.delta":
        delta = item.get("delta")
        return ChatDelta(content=delta if isinstance(delta, str) else "")

    reasoning_event_types = {
        "response.reasoning.delta",
        "response.reasoning_text.delta",
        "response.reasoning_summary_text.delta",
    }
    if event_type in reasoning_event_types:
        delta = item.get("delta")
        return ChatDelta(reasoning=delta if isinstance(delta, str) else "")

    if event_type == "response.completed":
        response = item.get("response")
        if not isinstance(response, dict) or response.get("status") != "completed":
            raise SSEParseError(
                "Responses API completion event did not report status 'completed'"
            )
        usage = response.get("usage") if isinstance(response, dict) else None
        normalized_usage = dict(usage) if isinstance(usage, dict) else None
        if normalized_usage is not None:
            input_tokens = normalized_usage.get("input_tokens")
            output_tokens = normalized_usage.get("output_tokens")
            if isinstance(input_tokens, int):
                normalized_usage.setdefault("prompt_tokens", input_tokens)
            if isinstance(output_tokens, int):
                normalized_usage.setdefault("completion_tokens", output_tokens)
        return ChatDelta(
            finish_reason="stop",
            usage=normalized_usage,
            response_metadata=_response_metadata(response),
            done=True,
        )

    if event_type in {"response.created", "response.in_progress"}:
        response = item.get("response")
        if isinstance(response, dict):
            return ChatDelta(response_metadata=_response_metadata(response))

    if event_type in {"error", "response.failed", "response.incomplete"}:
        response = item.get("response")
        error = response.get("error") if isinstance(response, dict) else None
        if not isinstance(error, dict):
            error = item.get("error")
        message = error.get("message") if isinstance(error, dict) else None
        detail = message if isinstance(message, str) else str(event_type)
        raise SSEParseError(f"Responses API failed: {detail}")

    return ChatDelta()
