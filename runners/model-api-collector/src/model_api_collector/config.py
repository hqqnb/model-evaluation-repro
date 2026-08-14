import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from dotenv import dotenv_values

from model_api_collector.models import ModelConfig, Settings


class ConfigError(ValueError):
    pass


def _environment(env_file: Optional[Union[str, Path]]) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if env_file is not None:
        values.update(
            {
                key: value
                for key, value in dotenv_values(env_file).items()
                if value is not None
            }
        )
    values.update(os.environ)
    return values


def load_settings(
    path: Union[str, Path], env_file: Optional[Union[str, Path]] = None
) -> Settings:
    config_path = Path(path)
    try:
        raw: Any = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigError(f"Cannot read model config {config_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ConfigError("Model config must be a YAML object")

    raw_models = raw.get("models")
    if not isinstance(raw_models, dict) or not raw_models:
        raise ConfigError("Model config must contain at least one model")

    models: Dict[str, ModelConfig] = {}
    for alias, item in raw_models.items():
        if not isinstance(alias, str) or not alias.strip():
            raise ConfigError("Every model alias must be a non-empty string")
        if not isinstance(item, dict):
            raise ConfigError(f"Model {alias!r} must be a YAML object")
        model_id = item.get("model")
        if not isinstance(model_id, str) or not model_id.strip():
            raise ConfigError(f"Model {alias!r} requires a non-empty model ID")
        endpoint = item.get("endpoint", "/v1/chat/completions")
        if not isinstance(endpoint, str) or not endpoint.startswith("/"):
            raise ConfigError(f"Model {alias!r} endpoint must start with '/'")
        stream = item.get("stream", False)
        if not isinstance(stream, bool):
            raise ConfigError(f"Model {alias!r} stream must be true or false")
        parameters = item.get("parameters", {})
        if not isinstance(parameters, dict):
            raise ConfigError(f"Model {alias!r} parameters must be an object")
        models[alias] = ModelConfig(
            alias=alias,
            model=model_id,
            endpoint=endpoint,
            stream=stream,
            parameters=dict(parameters),
        )

    environment = _environment(env_file)
    base_url = environment.get("ONEAPI_BASE_URL", "").strip().rstrip("/")
    api_key = environment.get("ONEAPI_API_KEY", "").strip()
    if not base_url:
        raise ConfigError("ONEAPI_BASE_URL is required")
    if not api_key:
        raise ConfigError("ONEAPI_API_KEY is required")
    try:
        timeout_seconds = float(environment.get("ONEAPI_TIMEOUT_SECONDS", "120"))
    except ValueError as exc:
        raise ConfigError("ONEAPI_TIMEOUT_SECONDS must be a number") from exc
    if timeout_seconds <= 0:
        raise ConfigError("ONEAPI_TIMEOUT_SECONDS must be greater than zero")
    try:
        complete_timeout_seconds = float(
            environment.get("ONEAPI_COMPLETE_TIMEOUT_SECONDS", "600")
        )
    except ValueError as exc:
        raise ConfigError(
            "ONEAPI_COMPLETE_TIMEOUT_SECONDS must be a number"
        ) from exc
    if complete_timeout_seconds <= 0:
        raise ConfigError(
            "ONEAPI_COMPLETE_TIMEOUT_SECONDS must be greater than zero"
        )
    try:
        max_attempts = int(environment.get("ONEAPI_MAX_ATTEMPTS", "3"))
    except ValueError as exc:
        raise ConfigError("ONEAPI_MAX_ATTEMPTS must be an integer") from exc
    if max_attempts < 1:
        raise ConfigError("ONEAPI_MAX_ATTEMPTS must be at least 1")

    return Settings(
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        models=models,
        max_attempts=max_attempts,
        complete_timeout_seconds=complete_timeout_seconds,
    )
