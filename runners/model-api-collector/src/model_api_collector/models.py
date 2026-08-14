from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class ModelConfig:
    alias: str
    model: str
    endpoint: str = "/v1/chat/completions"
    stream: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_key: str
    timeout_seconds: float
    models: Dict[str, ModelConfig]
    max_attempts: int = 3
    complete_timeout_seconds: float = 600


@dataclass(frozen=True)
class PromptCase:
    id: str
    title: str
    messages: List[Dict[str, Any]]
    tags: List[str] = field(default_factory=list)
    notes: str = ""
