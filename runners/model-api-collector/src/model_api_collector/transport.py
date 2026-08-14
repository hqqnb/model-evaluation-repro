import json
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import httpx

from model_api_collector.sse import (
    SSEDecoder,
    SSEParseError,
    extract_chat_delta,
    extract_responses_delta,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _elapsed_ms(start_ns: int) -> float:
    return (time.perf_counter_ns() - start_ns) / 1_000_000


def _uses_responses_api(endpoint: str) -> bool:
    return "/responses" in endpoint.rstrip("/")


def _normalize_responses_usage(usage):
    if not isinstance(usage, dict):
        return None
    normalized = dict(usage)
    input_tokens = normalized.get("input_tokens")
    output_tokens = normalized.get("output_tokens")
    if isinstance(input_tokens, int):
        normalized.setdefault("prompt_tokens", input_tokens)
    if isinstance(output_tokens, int):
        normalized.setdefault("completion_tokens", output_tokens)
    return normalized


@dataclass(frozen=True)
class TransportResult:
    started_at: str
    ended_at: str
    http_status: Optional[int]
    response_headers: Dict[str, str]
    content: str
    reasoning: str
    finish_reason: Optional[str]
    usage: Optional[Dict[str, Any]]
    time_to_headers_ms: Optional[float]
    time_to_first_event_ms: Optional[float]
    time_to_first_reasoning_ms: Optional[float]
    time_to_first_text_ms: Optional[float]
    total_time_ms: float
    completed_stream: bool
    error_type: Optional[str]
    error_message: Optional[str]
    error_body: Optional[str]
    response_metadata: Dict[str, Any] = field(default_factory=dict)
    attempt_count: int = 1
    attempt_errors: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def succeeded(self) -> bool:
        return self.error_type is None


class OneAPITransport:
    RETRYABLE_ERRORS = {
        "network_error",
        "timeout",
        "http_error",
        "stream_parse_error",
        "stream_read_error",
        "incomplete_stream",
        "incomplete_response",
        "empty_response",
    }

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout_seconds: float,
        max_attempts: int = 3,
        retry_backoff_seconds: float = 0.05,
        complete_timeout_seconds: Optional[float] = None,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if complete_timeout_seconds is not None and complete_timeout_seconds <= 0:
            raise ValueError(
                "complete_timeout_seconds must be greater than zero"
            )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.complete_timeout_seconds = (
            timeout_seconds
            if complete_timeout_seconds is None
            else complete_timeout_seconds
        )
        self.max_attempts = max_attempts
        self.retry_backoff_seconds = max(0.0, retry_backoff_seconds)

    def _redact(self, value: str) -> str:
        return value.replace(self.api_key, "[REDACTED]") if self.api_key else value

    def execute(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        raw_body_path: Union[str, Path],
    ) -> TransportResult:
        started_at = _utc_now()
        start_ns = time.perf_counter_ns()
        raw_path = Path(raw_body_path)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        attempt_errors = []
        selected_result = None

        for attempt_number in range(1, self.max_attempts + 1):
            attempt_path = (
                raw_path.with_name(
                    f"{raw_path.stem}.attempt-{attempt_number}{raw_path.suffix}"
                )
                if attempt_number < self.max_attempts
                else raw_path
            )
            result = self._execute_once(
                endpoint=endpoint,
                payload=payload,
                raw_path=attempt_path,
                start_ns=start_ns,
            )
            if result.succeeded:
                if attempt_path != raw_path and attempt_path.exists():
                    raw_path.write_bytes(attempt_path.read_bytes())
                selected_result = result
                break

            attempt_errors.append(
                {
                    "type": result.error_type,
                    "message": result.error_message,
                }
            )
            selected_result = result
            if not self._is_retryable(result, attempt_number):
                break
            if attempt_number < self.max_attempts:
                time.sleep(self.retry_backoff_seconds * attempt_number)

        assert selected_result is not None
        return replace(
            selected_result,
            started_at=started_at,
            ended_at=_utc_now(),
            total_time_ms=_elapsed_ms(start_ns),
            attempt_count=len(attempt_errors) + (1 if selected_result.succeeded else 0),
            attempt_errors=attempt_errors,
        )

    def _is_retryable(self, result: TransportResult, attempt_number: int) -> bool:
        if attempt_number >= self.max_attempts:
            return False
        if result.error_type not in self.RETRYABLE_ERRORS:
            return False
        if result.error_type == "http_error":
            if self._is_deterministic_http_error(result.error_body):
                return False
            return result.http_status == 429 or (
                result.http_status is not None and result.http_status >= 500
            )
        return True

    @staticmethod
    def _is_deterministic_http_error(error_body: Optional[str]) -> bool:
        if not error_body:
            return False
        try:
            payload = json.loads(error_body)
        except json.JSONDecodeError:
            payload = {}
        error = payload.get("error") if isinstance(payload, dict) else None
        error_type = error.get("type") if isinstance(error, dict) else None
        message = error.get("message") if isinstance(error, dict) else None
        if error_type in {
            "convert_request_failed",
            "not_implemented",
            "unsupported_parameter",
        }:
            return True
        return isinstance(message, str) and "not implemented" in message.lower()

    def _execute_once(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        raw_path: Path,
        start_ns: int,
    ) -> TransportResult:
        started_at = _utc_now()

        http_status: Optional[int] = None
        response_headers: Dict[str, str] = {}
        content_parts = []
        reasoning_parts = []
        finish_reason: Optional[str] = None
        usage: Optional[Dict[str, Any]] = None
        response_metadata: Dict[str, Any] = {}
        time_to_headers_ms: Optional[float] = None
        time_to_first_event_ms: Optional[float] = None
        time_to_first_reasoning_ms: Optional[float] = None
        time_to_first_text_ms: Optional[float] = None
        completed_stream = False
        error_type: Optional[str] = None
        error_message: Optional[str] = None
        error_body: Optional[str] = None

        try:
            request_timeout = (
                self.timeout_seconds
                if payload.get("stream", True)
                else self.complete_timeout_seconds
            )
            with httpx.Client(timeout=request_timeout) as client:
                with client.stream(
                    "POST",
                    f"{self.base_url}{endpoint}",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "Accept": (
                            "text/event-stream"
                            if payload.get("stream", True)
                            else "application/json"
                        ),
                    },
                    json=payload,
                ) as response:
                    http_status = response.status_code
                    response_headers = dict(response.headers)
                    time_to_headers_ms = _elapsed_ms(start_ns)

                    if response.status_code < 200 or response.status_code >= 300:
                        body = self._read_body(response, raw_path)
                        error_body = self._redact(body.decode("utf-8", errors="replace"))
                        error_type = "http_error"
                        error_message = f"OneAPI returned HTTP {response.status_code}"
                    elif payload.get("stream", True):
                        (
                            content_parts,
                            reasoning_parts,
                            finish_reason,
                            usage,
                            response_metadata,
                            time_to_first_event_ms,
                            time_to_first_reasoning_ms,
                            time_to_first_text_ms,
                            completed_stream,
                            error_type,
                            error_message,
                        ) = self._read_stream(
                            response,
                            raw_path,
                            start_ns,
                            responses_api=_uses_responses_api(endpoint),
                        )
                    else:
                        (
                            content_parts,
                            reasoning_parts,
                            finish_reason,
                            usage,
                            response_metadata,
                            error_type,
                            error_message,
                        ) = self._read_json(
                            response,
                            raw_path,
                            responses_api=_uses_responses_api(endpoint),
                        )
        except httpx.TimeoutException as exc:
            error_type = "timeout"
            error_message = self._redact(str(exc) or "OneAPI request timed out")
        except httpx.HTTPError as exc:
            error_type = "stream_read_error" if raw_path.exists() else "network_error"
            error_message = self._redact(str(exc))

        ended_at = _utc_now()
        return TransportResult(
            started_at=started_at,
            ended_at=ended_at,
            http_status=http_status,
            response_headers=response_headers,
            content="".join(content_parts),
            reasoning="".join(reasoning_parts),
            finish_reason=finish_reason,
            usage=usage,
            time_to_headers_ms=time_to_headers_ms,
            time_to_first_event_ms=time_to_first_event_ms,
            time_to_first_reasoning_ms=time_to_first_reasoning_ms,
            time_to_first_text_ms=time_to_first_text_ms,
            total_time_ms=_elapsed_ms(start_ns),
            completed_stream=completed_stream,
            error_type=error_type,
            error_message=error_message,
            error_body=error_body,
            response_metadata=response_metadata,
            attempt_count=1,
            attempt_errors=[],
        )

    def _read_stream(
        self,
        response,
        raw_path: Path,
        start_ns: int,
        responses_api: bool = False,
    ):
        decoder = SSEDecoder()
        extract_delta = (
            extract_responses_delta if responses_api else extract_chat_delta
        )
        content_parts = []
        reasoning_parts = []
        finish_reason = None
        usage = None
        response_metadata = {}
        first_event_ms = None
        first_reasoning_ms = None
        first_text_ms = None
        completed = False
        parse_error = None

        def record_payloads(payloads):
            nonlocal completed
            nonlocal finish_reason
            nonlocal first_event_ms
            nonlocal first_reasoning_ms
            nonlocal first_text_ms
            nonlocal usage
            nonlocal response_metadata

            for payload in payloads:
                if first_event_ms is None:
                    first_event_ms = _elapsed_ms(start_ns)
                delta = extract_delta(payload)
                if delta.content:
                    content_parts.append(delta.content)
                if delta.reasoning:
                    reasoning_parts.append(delta.reasoning)
                    if first_reasoning_ms is None:
                        first_reasoning_ms = _elapsed_ms(start_ns)
                if first_text_ms is None and delta.content:
                    first_text_ms = _elapsed_ms(start_ns)
                if delta.finish_reason is not None:
                    finish_reason = delta.finish_reason
                if delta.usage is not None:
                    usage = delta.usage
                if delta.response_metadata is not None:
                    response_metadata.update(delta.response_metadata)
                if delta.done:
                    completed = True

        with raw_path.open("wb") as raw_file:
            for chunk in response.iter_bytes():
                raw_file.write(chunk)
                if parse_error is not None:
                    continue
                try:
                    record_payloads(decoder.feed(chunk))
                except SSEParseError as exc:
                    parse_error = self._redact(str(exc))
            if parse_error is None:
                try:
                    record_payloads(decoder.finish())
                except SSEParseError as exc:
                    parse_error = self._redact(str(exc))

        if parse_error is not None:
            return (
                content_parts,
                reasoning_parts,
                finish_reason,
                usage,
                response_metadata,
                first_event_ms,
                first_reasoning_ms,
                first_text_ms,
                completed,
                "stream_parse_error",
                parse_error,
            )
        if not completed:
            return (
                content_parts,
                reasoning_parts,
                finish_reason,
                usage,
                response_metadata,
                first_event_ms,
                first_reasoning_ms,
                first_text_ms,
                False,
                "incomplete_stream",
                "Stream ended before a completion event",
            )
        if not responses_api and finish_reason is None:
            return (
                content_parts,
                reasoning_parts,
                finish_reason,
                usage,
                response_metadata,
                first_event_ms,
                first_reasoning_ms,
                first_text_ms,
                True,
                "incomplete_stream",
                "Stream completed without a finish reason",
            )
        if not "".join(content_parts).strip():
            return (
                content_parts,
                reasoning_parts,
                finish_reason,
                usage,
                response_metadata,
                first_event_ms,
                first_reasoning_ms,
                first_text_ms,
                True,
                "empty_response",
                "Stream completed without visible answer text",
            )
        if finish_reason == "length":
            return (
                content_parts,
                reasoning_parts,
                finish_reason,
                usage,
                response_metadata,
                first_event_ms,
                first_reasoning_ms,
                first_text_ms,
                True,
                "output_limit",
                "Stream ended because the output limit was reached",
            )
        return (
            content_parts,
            reasoning_parts,
            finish_reason,
            usage,
            response_metadata,
            first_event_ms,
            first_reasoning_ms,
            first_text_ms,
            True,
            None,
            None,
        )

    @staticmethod
    def _read_body(response, raw_path: Path) -> bytes:
        chunks = []
        with raw_path.open("wb") as raw_file:
            for chunk in response.iter_bytes():
                raw_file.write(chunk)
                chunks.append(chunk)
        return b"".join(chunks)

    def _read_json(self, response, raw_path: Path, responses_api: bool = False):
        body = self._read_body(response, raw_path)
        try:
            item = json.loads(body)
            response_metadata = self._extract_response_metadata(
                item, responses_api=responses_api
            )
            if responses_api:
                content_parts = []
                output = item.get("output")
                if isinstance(output, list):
                    for output_item in output:
                        if not isinstance(output_item, dict):
                            continue
                        content = output_item.get("content")
                        if not isinstance(content, list):
                            continue
                        for content_item in content:
                            if (
                                isinstance(content_item, dict)
                                and content_item.get("type") == "output_text"
                                and isinstance(content_item.get("text"), str)
                            ):
                                content_parts.append(content_item["text"])
                status = item.get("status")
                if status != "completed":
                    return (
                        content_parts,
                        [],
                        None,
                        _normalize_responses_usage(item.get("usage")),
                        response_metadata,
                        "incomplete_response",
                        f"Responses response status was {status!r}",
                    )
                if not "".join(content_parts).strip():
                    return (
                        content_parts,
                        [],
                        "stop",
                        _normalize_responses_usage(item.get("usage")),
                        response_metadata,
                        "empty_response",
                        "Responses response completed without visible answer text",
                    )
                return (
                    content_parts,
                    [],
                    "stop" if status == "completed" else None,
                    _normalize_responses_usage(item.get("usage")),
                    response_metadata,
                    None,
                    None,
                )
            choice = item["choices"][0]
            message = choice["message"]
            content = message.get("content")
            reasoning = message.get("reasoning_content")
            usage = item.get("usage")
            if not isinstance(content, str) or not content.strip():
                return (
                    [],
                    [reasoning] if isinstance(reasoning, str) else [],
                    choice.get("finish_reason"),
                    usage if isinstance(usage, dict) else None,
                    response_metadata,
                    "empty_response",
                    "Chat response completed without visible answer text",
                )
            if choice.get("finish_reason") == "length":
                return (
                    [content],
                    [reasoning] if isinstance(reasoning, str) else [],
                    "length",
                    usage if isinstance(usage, dict) else None,
                    response_metadata,
                    "output_limit",
                    "Chat response ended because the output limit was reached",
                )
            return (
                [content] if isinstance(content, str) else [],
                [reasoning] if isinstance(reasoning, str) else [],
                choice.get("finish_reason"),
                usage if isinstance(usage, dict) else None,
                response_metadata,
                None,
                None,
            )
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            return (
                [],
                [],
                None,
                {},
                None,
                "response_parse_error",
                self._redact(f"Invalid non-streaming response: {exc}"),
            )

    @staticmethod
    def _extract_response_metadata(
        item: Any, responses_api: bool
    ) -> Dict[str, Any]:
        if not isinstance(item, dict):
            return {}
        if responses_api:
            return {
                "model": item.get("model"),
                "status": item.get("status"),
                "temperature": item.get("temperature"),
                "top_p": item.get("top_p"),
                "reasoning": item.get("reasoning"),
                "tools": item.get("tools"),
            }
        return {
            key: item[key]
            for key in ("model", "system_fingerprint", "service_tier")
            if key in item
        }
