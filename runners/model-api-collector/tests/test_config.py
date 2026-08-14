from pathlib import Path

import pytest

from model_api_collector.config import ConfigError, load_settings


def write_models(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_load_settings_reads_secret_from_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("ONEAPI_BASE_URL", "http://localhost:9000/")
    monkeypatch.setenv("ONEAPI_API_KEY", "secret-value")
    path = tmp_path / "models.yaml"
    write_models(
        path,
        "models:\n"
        "  alpha:\n"
        "    model: provider/model-a\n"
        "    parameters:\n"
        "      temperature: 0\n",
    )

    settings = load_settings(path)

    assert settings.base_url == "http://localhost:9000"
    assert settings.api_key == "secret-value"
    assert settings.timeout_seconds == 120
    assert settings.complete_timeout_seconds == 600
    assert settings.max_attempts == 3
    assert settings.models["alpha"].model == "provider/model-a"
    assert settings.models["alpha"].endpoint == "/v1/chat/completions"
    assert settings.models["alpha"].stream is False
    assert settings.models["alpha"].parameters == {"temperature": 0}


def test_canonical_config_uses_streaming_for_claude_responses_models(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("ONEAPI_BASE_URL", "http://localhost:9000")
    monkeypatch.setenv("ONEAPI_API_KEY", "secret-value")

    settings = load_settings(Path(__file__).parents[1] / "config/models.yaml")

    assert settings.models["opus-5"].stream is True
    assert settings.models["opus-4.8"].stream is True
    assert settings.models["gpt-5.5"].stream is False
    assert settings.models["gpt-5.6-sol"].stream is False


def test_canonical_model_configs_request_highest_reasoning_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("ONEAPI_BASE_URL", "http://localhost:9000")
    monkeypatch.setenv("ONEAPI_API_KEY", "secret-value")

    project_root = Path(__file__).parents[1]
    expected = {
        "config/models.yaml": {
            "glm-5.2": "max",
            "gpt-5.6-sol": "max",
            "gpt-5.5": "xhigh",
            "opus-5": "max",
            "opus-4.8": "max",
            "deepseek-v4-flash": "max",
        },
        "config/qwen.yaml": {"qwen3.8-max": "max"},
        "config/kimi.yaml": {"kimi-k3": "max"},
        "config/hy3.yaml": {"hy3": "high"},
        "config/deepseek-official.yaml": {"deepseek-v4-pro": "max"},
        "config/deepseek-v4-pro-2x.yaml": {
            "deepseek-v4-pro-r1": "max",
            "deepseek-v4-pro-r2": "max",
        },
    }

    for relative_path, model_modes in expected.items():
        settings = load_settings(project_root / relative_path)
        assert {
            alias: model.parameters["reasoning_effort"]
            for alias, model in settings.models.items()
        } == model_modes


def test_load_settings_reads_retry_limit_from_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("ONEAPI_BASE_URL", "http://localhost:9000")
    monkeypatch.setenv("ONEAPI_API_KEY", "secret-value")
    monkeypatch.setenv("ONEAPI_MAX_ATTEMPTS", "5")
    path = tmp_path / "models.yaml"
    write_models(path, "models:\n  alpha:\n    model: provider/model-a\n")

    settings = load_settings(path)

    assert settings.max_attempts == 5


def test_real_environment_takes_precedence_over_env_file(tmp_path, monkeypatch):
    monkeypatch.setenv("ONEAPI_BASE_URL", "http://real.example")
    monkeypatch.setenv("ONEAPI_API_KEY", "real-secret")
    env_path = tmp_path / ".env"
    env_path.write_text(
        "ONEAPI_BASE_URL=http://file.example\nONEAPI_API_KEY=file-secret\n",
        encoding="utf-8",
    )
    config_path = tmp_path / "models.yaml"
    write_models(config_path, "models:\n  alpha:\n    model: model-a\n")

    settings = load_settings(config_path, env_file=env_path)

    assert settings.base_url == "http://real.example"
    assert settings.api_key == "real-secret"


def test_load_settings_rejects_missing_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("ONEAPI_BASE_URL", "http://localhost:9000")
    monkeypatch.delenv("ONEAPI_API_KEY", raising=False)
    path = tmp_path / "models.yaml"
    write_models(path, "models:\n  alpha:\n    model: model-a\n")

    with pytest.raises(ConfigError, match="ONEAPI_API_KEY"):
        load_settings(path)


@pytest.mark.parametrize(
    "yaml_text, message",
    [
        ("models: {}\n", "at least one model"),
        ("models:\n  alpha: {}\n", "model ID"),
        ("models:\n  alpha:\n    model: ''\n", "model ID"),
    ],
)
def test_load_settings_rejects_invalid_models(
    tmp_path, monkeypatch, yaml_text, message
):
    monkeypatch.setenv("ONEAPI_BASE_URL", "http://localhost:9000")
    monkeypatch.setenv("ONEAPI_API_KEY", "secret")
    path = tmp_path / "models.yaml"
    write_models(path, yaml_text)

    with pytest.raises(ConfigError, match=message):
        load_settings(path)
