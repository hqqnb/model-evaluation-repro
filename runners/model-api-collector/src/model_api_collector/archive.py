import csv
import hashlib
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


SUMMARY_COLUMNS = [
    "run_id",
    "request_id",
    "prompt_id",
    "model_alias",
    "model",
    "status",
    "http_status",
    "time_to_first_event_ms",
    "time_to_first_reasoning_ms",
    "time_to_first_text_ms",
    "total_time_ms",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "raw_response_path",
    "response_text_path",
    "error_type",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


@dataclass
class RunArchive:
    run_path: Path
    run_id: str
    api_key: str
    _request_hashes: Dict[str, str] = field(default_factory=dict)
    _summary_rows: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        root: Union[str, Path],
        run_metadata: Dict[str, Any],
        api_key: str,
    ) -> "RunArchive":
        run_id = run_metadata.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("run_metadata requires a non-empty run_id")
        run_path = Path(root) / run_id
        run_path.mkdir(parents=True, exist_ok=False)
        (run_path / "requests").mkdir()
        archive = cls(run_path=run_path, run_id=run_id, api_key=api_key)
        metadata = dict(run_metadata)
        metadata.setdefault("created_at", _utc_now())
        archive._write_json(run_path / "run.json", metadata)
        (run_path / "results.jsonl").touch()
        return archive

    def _redact(self, value: Any) -> Any:
        if isinstance(value, str):
            return value.replace(self.api_key, "[REDACTED]") if self.api_key else value
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        if isinstance(value, dict):
            return {key: self._redact(item) for key, item in value.items()}
        return value

    def _write_json(self, path: Path, value: Any) -> None:
        safe_value = self._redact(value)
        content = (
            json.dumps(safe_value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
        self._atomic_write(path, content)

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            temp_path.write_bytes(content)
            os.replace(temp_path, path)
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def start_request(self, request_id: str, payload: Dict[str, Any]) -> Path:
        request_dir = self.run_path / "requests" / request_id
        request_dir.mkdir(parents=True, exist_ok=False)
        safe_payload = self._redact(payload)
        self._request_hashes[request_id] = hashlib.sha256(
            _canonical_json_bytes(safe_payload)
        ).hexdigest()
        self._write_json(request_dir / "request.json", safe_payload)
        return request_dir

    def finish_request(
        self,
        request_id: str,
        response_headers: Dict[str, str],
        content: str,
        reasoning: str,
        metadata: Dict[str, Any],
        error: Optional[Dict[str, Any]] = None,
    ) -> None:
        request_dir = self.run_path / "requests" / request_id
        if request_id not in self._request_hashes or not request_dir.is_dir():
            raise ValueError(f"Unknown request ID {request_id!r}")

        self._write_json(request_dir / "response-headers.json", response_headers)
        self._atomic_write(
            request_dir / "response.md",
            self._redact(content).encode("utf-8"),
        )
        if reasoning:
            self._atomic_write(
                request_dir / "reasoning.md",
                self._redact(reasoning).encode("utf-8"),
            )

        record = dict(metadata)
        record.update(
            {
                "run_id": self.run_id,
                "request_id": request_id,
                "request_sha256": self._request_hashes[request_id],
                "response_text_path": (
                    f"requests/{request_id}/response.md"
                ),
            }
        )
        if reasoning:
            record["reasoning_text_path"] = f"requests/{request_id}/reasoning.md"
        self._write_json(request_dir / "metadata.json", record)
        if error is not None:
            self._write_json(request_dir / "error.json", error)

        result = self._result_index(record, error)
        safe_result = self._redact(result)
        with (self.run_path / "results.jsonl").open("a", encoding="utf-8") as file:
            file.write(json.dumps(safe_result, ensure_ascii=False, sort_keys=True))
            file.write("\n")
        self._summary_rows.append(safe_result)

    def _result_index(
        self, metadata: Dict[str, Any], error: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        usage = metadata.get("usage")
        if not isinstance(usage, dict):
            usage = {}
        return {
            "run_id": self.run_id,
            "request_id": metadata["request_id"],
            "prompt_id": metadata.get("prompt_id"),
            "model_alias": metadata.get("model_alias"),
            "model": metadata.get("model"),
            "status": metadata.get("status"),
            "http_status": metadata.get("http_status"),
            "time_to_first_event_ms": metadata.get("time_to_first_event_ms"),
            "time_to_first_reasoning_ms": metadata.get(
                "time_to_first_reasoning_ms"
            ),
            "time_to_first_text_ms": metadata.get("time_to_first_text_ms"),
            "total_time_ms": metadata.get("total_time_ms"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "total_tokens": usage.get("total_tokens"),
            "raw_response_path": metadata.get("raw_response_path"),
            "response_text_path": metadata.get("response_text_path"),
            "error_type": error.get("type") if error else None,
        }

    def finalize(self) -> None:
        temp_path = self.run_path / ".summary.csv.tmp"
        with temp_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=SUMMARY_COLUMNS)
            writer.writeheader()
            writer.writerows(self._summary_rows)
        os.replace(temp_path, self.run_path / "summary.csv")
