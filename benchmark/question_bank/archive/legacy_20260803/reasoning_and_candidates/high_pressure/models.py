from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass(frozen=True)
class Component:
    field: str
    points: int
    mode: str = "exact"


@dataclass(frozen=True)
class TaskCase:
    id: str
    title: str
    prompt: str
    expected: Dict[str, Any]
    near_miss: Dict[str, Any]
    components: Tuple[Component, ...]


@dataclass(frozen=True)
class GradeResult:
    task_id: str
    points: int
    whole_correct: bool
    status: str
    format_compliant: bool
    component_results: Dict[str, bool]
    parsed_answer: Any = None
    error: str = ""
