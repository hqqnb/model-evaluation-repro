import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Union

from model_api_collector.archive import RunArchive
from model_api_collector.config import ConfigError
from model_api_collector.models import PromptCase, Settings
from model_api_collector.transport import OneAPITransport


RESERVED_PARAMETERS = {"model", "messages", "input", "stream"}
DELIVERY_MODES = {"complete", "stream"}


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    run_path: Path
    total: int
    successful: int
    failed: int


def _new_run_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{timestamp}-{uuid.uuid4().hex[:8]}"


def _build_payload(
    model_config, prompt_case: PromptCase, delivery_mode: Optional[str] = None
):
    prompt_key = (
        "input"
        if "/responses" in model_config.endpoint.rstrip("/")
        else "messages"
    )
    stream = (
        model_config.stream
        if delivery_mode is None
        else delivery_mode == "stream"
    )
    return {
        "model": model_config.model,
        prompt_key: prompt_case.messages,
        **model_config.parameters,
        "stream": stream,
    }


def _requested_parameters(payload):
    return {
        key: value
        for key, value in payload.items()
        if key not in {"model", "messages", "input", "stream"}
    }


def _validate_run(
    settings: Settings,
    model_aliases: Iterable[str],
    prompt_cases: List[PromptCase],
    repeat: int,
    delivery_mode: Optional[str] = None,
    max_attempts: Optional[int] = None,
) -> List[str]:
    aliases = list(model_aliases)
    if not aliases:
        raise ConfigError("At least one model alias is required")
    if repeat < 1:
        raise ConfigError("Repeat must be at least 1")
    if not prompt_cases:
        raise ConfigError("At least one prompt is required")
    if delivery_mode is not None and delivery_mode not in DELIVERY_MODES:
        raise ConfigError(
            f"Delivery mode must be one of: {', '.join(sorted(DELIVERY_MODES))}"
        )
    if max_attempts is not None and max_attempts < 1:
        raise ConfigError("max_attempts must be at least 1")
    for alias in aliases:
        if alias not in settings.models:
            raise ConfigError(f"Unknown model alias {alias!r}")
        reserved = RESERVED_PARAMETERS.intersection(
            settings.models[alias].parameters
        )
        if reserved:
            names = ", ".join(sorted(reserved))
            raise ConfigError(
                f"Model {alias!r} parameters contain reserved keys: {names}"
            )
    return aliases


def run_evaluation(
    settings: Settings,
    model_aliases: Iterable[str],
    prompt_cases: List[PromptCase],
    repeat: int,
    output_root: Union[str, Path],
    config_sha256: str,
    prompts_sha256: str,
    transport: Optional[OneAPITransport] = None,
    delivery_mode: Optional[str] = None,
    max_attempts: Optional[int] = None,
) -> RunSummary:
    aliases = _validate_run(
        settings,
        model_aliases,
        prompt_cases,
        repeat,
        delivery_mode=delivery_mode,
        max_attempts=max_attempts,
    )
    run_id = _new_run_id()
    effective_max_attempts = (
        settings.max_attempts if max_attempts is None else max_attempts
    )
    archive = RunArchive.create(
        root=output_root,
        run_metadata={
            "run_id": run_id,
            "oneapi_base_url": settings.base_url,
            "model_aliases": aliases,
            "prompt_ids": [case.id for case in prompt_cases],
            "repeat": repeat,
            "delivery_mode": delivery_mode or "model",
            "max_attempts": effective_max_attempts,
            "config_sha256": config_sha256,
            "prompts_sha256": prompts_sha256,
        },
        api_key=settings.api_key,
    )
    active_transport = transport or OneAPITransport(
        base_url=settings.base_url,
        api_key=settings.api_key,
        timeout_seconds=settings.timeout_seconds,
        complete_timeout_seconds=settings.complete_timeout_seconds,
        max_attempts=effective_max_attempts,
    )

    successful = 0
    failed = 0
    for alias in aliases:
        model_config = settings.models[alias]
        for prompt_case in prompt_cases:
            for repeat_index in range(1, repeat + 1):
                request_id = uuid.uuid4().hex
                payload = _build_payload(
                    model_config, prompt_case, delivery_mode=delivery_mode
                )
                request_dir = archive.start_request(request_id, payload)
                raw_name = "response.sse" if payload["stream"] else "response.json"
                raw_path = request_dir / raw_name
                result = active_transport.execute(
                    endpoint=model_config.endpoint,
                    payload=payload,
                    raw_body_path=raw_path,
                )
                status = "success" if result.succeeded else "failed"
                if result.succeeded:
                    successful += 1
                else:
                    failed += 1

                error = None
                if not result.succeeded:
                    error = {
                        "type": result.error_type,
                        "message": result.error_message,
                        "body": result.error_body,
                    }
                archive.finish_request(
                    request_id,
                    response_headers=result.response_headers,
                    content=result.content,
                    reasoning=result.reasoning,
                    metadata={
                        "prompt_id": prompt_case.id,
                        "prompt_title": prompt_case.title,
                        "prompt_tags": prompt_case.tags,
                        "prompt_notes": prompt_case.notes,
                        "model_alias": alias,
                        "model": model_config.model,
                        "endpoint": model_config.endpoint,
                        "repeat_index": repeat_index,
                        "status": status,
                        "started_at": result.started_at,
                        "ended_at": result.ended_at,
                        "http_status": result.http_status,
                        "finish_reason": result.finish_reason,
                        "completed_stream": result.completed_stream,
                        "time_to_headers_ms": result.time_to_headers_ms,
                        "time_to_first_event_ms": result.time_to_first_event_ms,
                        "time_to_first_reasoning_ms": (
                            result.time_to_first_reasoning_ms
                        ),
                        "time_to_first_text_ms": result.time_to_first_text_ms,
                        "total_time_ms": result.total_time_ms,
                        "usage": result.usage,
                        "requested_parameters": _requested_parameters(payload),
                        "effective_parameters": result.response_metadata,
                        "attempt_count": result.attempt_count,
                        "attempt_errors": result.attempt_errors,
                        "raw_response_path": (
                            f"requests/{request_id}/{raw_name}"
                        ),
                    },
                    error=error,
                )

    archive.finalize()
    return RunSummary(
        run_id=run_id,
        run_path=archive.run_path,
        total=successful + failed,
        successful=successful,
        failed=failed,
    )
