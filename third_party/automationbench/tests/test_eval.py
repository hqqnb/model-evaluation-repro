from automationbench.scripts.eval import _client_request_timeout, _openai_client_config


def test_client_request_timeout_prefers_oneapi_timeout(monkeypatch):
    monkeypatch.delenv("AUTO_BENCH_REQUEST_TIMEOUT_SECONDS", raising=False)
    monkeypatch.setenv("ONEAPI_TIMEOUT_SECONDS", "300")

    assert _client_request_timeout() == 300.0


def test_openai_client_config_disables_sdk_retries(monkeypatch):
    monkeypatch.setenv("ONEAPI_TIMEOUT_SECONDS", "45")

    config = _openai_client_config("ONEAPI_API_KEY", "https://tokenhub.tencentmaas.com/v1")

    assert config.timeout == 45.0
    assert config.max_retries == 0
