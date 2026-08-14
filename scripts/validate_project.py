#!/usr/bin/env python3
"""Validate repository layout and provider/model configuration without making API calls."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any


SUPPORTED_PROTOCOLS = {"chat_completions", "responses", "anthropic"}
ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]*$")


def validate_provider_config(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    providers = config.get("providers")
    if not isinstance(providers, dict) or not providers:
        return ["providers must be a non-empty mapping"]

    for name, provider in providers.items():
        if not isinstance(provider, dict):
            errors.append(f"provider {name} must be a mapping")
            continue
        if "api_key" in provider:
            errors.append(f"provider {name} must use api_key_env, not api_key")
        base_url = provider.get("base_url")
        if not isinstance(base_url, str) or not base_url.startswith(("http://", "https://")):
            errors.append(f"provider {name} must define an http(s) base_url")
        api_key_env = provider.get("api_key_env")
        if not isinstance(api_key_env, str) or not ENV_NAME.fullmatch(api_key_env):
            errors.append(f"provider {name} must define an uppercase api_key_env")
        protocol = provider.get("protocol")
        if protocol not in SUPPORTED_PROTOCOLS:
            errors.append(f"provider {name} uses unsupported protocol {protocol}")
    return errors


def validate_model_config(
    config: dict[str, Any], provider_names: set[str]
) -> list[str]:
    errors: list[str] = []
    models = config.get("models")
    if not isinstance(models, dict) or not models:
        return ["models must be a non-empty mapping"]

    for name, model in models.items():
        if not isinstance(model, dict):
            errors.append(f"model {name} must be a mapping")
            continue
        provider = model.get("provider")
        if provider not in provider_names:
            errors.append(f"model {name} references unknown provider {provider}")
        model_id = model.get("model")
        if not isinstance(model_id, str) or not model_id.strip():
            errors.append(f"model {name} must define a model ID")
        protocol = model.get("protocol")
        if protocol not in SUPPORTED_PROTOCOLS:
            errors.append(f"model {name} uses unsupported protocol {protocol}")
    return errors


def validate_repository_layout(root: Path) -> list[str]:
    required = (
        ("README.md", False),
        ("configs/providers.example.yaml", False),
        ("configs/models.example.yaml", False),
        ("benchmark", True),
        ("runners", True),
        ("evaluation", True),
        ("scripts", True),
    )
    errors: list[str] = []
    for relative, is_dir in required:
        path = root / relative
        if not path.exists():
            errors.append(f"{relative} is missing")
        elif is_dir and not path.is_dir():
            errors.append(f"{relative} is not a directory")
    return errors


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - exercised in clean setup
        raise RuntimeError("PyYAML is required to read repository config files") from exc
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return value


def validate_files(root: Path, providers_path: Path, models_path: Path) -> list[str]:
    errors = validate_repository_layout(root)
    if errors:
        return errors
    providers = _load_yaml(providers_path)
    provider_errors = validate_provider_config(providers)
    provider_names = set(providers.get("providers", {}))
    models = _load_yaml(models_path)
    return provider_errors + validate_model_config(models, provider_names)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--providers", type=Path, default=Path("configs/providers.example.yaml"))
    parser.add_argument("--models", type=Path, default=Path("configs/models.example.yaml"))
    args = parser.parse_args(argv)

    root = args.root.resolve()
    providers_path = args.providers if args.providers.is_absolute() else root / args.providers
    models_path = args.models if args.models.is_absolute() else root / args.models
    try:
        errors = validate_files(root, providers_path, models_path)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"validation error: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"Repository validation passed: {root}")
    print(f"Configured providers: {', '.join(sorted(_load_yaml(providers_path)['providers']))}")
    print(f"Configured models: {', '.join(sorted(_load_yaml(models_path)['models']))}")
    print(f"Live API key variables present: {sum(bool(os.environ.get(name)) for name in _key_names(providers_path))}")
    return 0


def _key_names(providers_path: Path) -> list[str]:
    providers = _load_yaml(providers_path).get("providers", {})
    return [
        provider["api_key_env"]
        for provider in providers.values()
        if isinstance(provider, dict) and isinstance(provider.get("api_key_env"), str)
    ]


if __name__ == "__main__":
    raise SystemExit(main())
