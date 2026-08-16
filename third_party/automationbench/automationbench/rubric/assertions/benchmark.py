# Copyright 2026 Zapier, Inc.
# SPDX-License-Identifier: MIT

"""Assertions for the formal eight-task Agent benchmark."""

from __future__ import annotations

import re

from automationbench.rubric.registry import AssertionRegistry
from automationbench.schema.world import WorldState


def _called(world: WorldState, tool: str) -> bool:
    return any(item.get("tool") == tool for item in world.banking.tool_log)


def _benchmark_called(world: WorldState, tool: str) -> bool:
    return any(item.get("tool") == tool for item in world.benchmark.tool_log)


def _actions(world: WorldState, kind: str | None = None) -> list[dict]:
    if kind is None:
        return list(world.benchmark.actions)
    return [item for item in world.benchmark.actions if item.get("kind") == kind]


def _get_path(value, path: str):
    for part in path.split("."):
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def _contains(value, needles: list[str]) -> bool:
    text = str(value).lower()
    return all(str(needle).lower() in text for needle in needles)


def _contains_concepts(
    value,
    concepts: list[list[str]],
    minimum: int | None = None,
) -> bool:
    text = str(value).lower()
    matched = [
        any(str(alias).lower() in text for alias in aliases)
        for aliases in concepts
    ]
    required = len(concepts) if minimum is None else int(minimum)
    return sum(matched) >= required


@AssertionRegistry.register("benchmark_tool_called")
def benchmark_tool_called(world: WorldState, assertion: dict) -> bool:
    return _benchmark_called(world, assertion["tool"])


@AssertionRegistry.register("benchmark_tool_called_count")
def benchmark_tool_called_count(world: WorldState, assertion: dict) -> bool:
    count = sum(1 for item in world.benchmark.tool_log if item.get("tool") == assertion["tool"])
    return count >= int(assertion.get("at_least", 1))


@AssertionRegistry.register("benchmark_distinct_files_read")
def benchmark_distinct_files_read(world: WorldState, assertion: dict) -> bool:
    paths: set[str] = set()
    for item in world.benchmark.tool_log:
        tool = item.get("tool")
        arguments = item.get("arguments", {})
        if tool == "benchmark_analysis_read_file" and arguments.get("path"):
            paths.add(str(arguments["path"]))
        elif tool == "benchmark_analysis_read_files":
            paths.update(str(path) for path in arguments.get("paths", []))
    return len(paths) >= int(assertion.get("minimum", 1))


@AssertionRegistry.register("benchmark_action_count")
def benchmark_action_count(world: WorldState, assertion: dict) -> bool:
    count = len(_actions(world, assertion["kind"]))
    if "at_least" in assertion:
        return count >= int(assertion["at_least"])
    return count == int(assertion.get("count", 0))


@AssertionRegistry.register("benchmark_action_exists")
def benchmark_action_exists(world: WorldState, assertion: dict) -> bool:
    for action in _actions(world, assertion["kind"]):
        expected = assertion.get("contains", {})
        if all(str(action.get(key, "")).lower().find(str(value).lower()) >= 0 for key, value in expected.items()):
            return True
    return False


@AssertionRegistry.register("benchmark_action_ids_equal")
def benchmark_action_ids_equal(world: WorldState, assertion: dict) -> bool:
    actual = [
        item.get(assertion["id_key"])
        for item in _actions(world, assertion["kind"])
        if item.get(assertion["id_key"]) is not None
    ]
    expected = list(assertion.get("expected", []))
    return len(actual) == len(set(actual)) and set(actual) == set(expected)


@AssertionRegistry.register("benchmark_actions_match")
def benchmark_actions_match(world: WorldState, assertion: dict) -> bool:
    expected = assertion.get("expected", {})
    actual = {
        item.get(assertion["id_key"]): item.get(assertion["value_key"])
        for item in _actions(world, assertion["kind"])
    }
    return actual == expected


@AssertionRegistry.register("benchmark_actions_unique")
def benchmark_actions_unique(world: WorldState, assertion: dict) -> bool:
    for kind in assertion.get("kinds", []):
        items = _actions(world, kind)
        if kind in {"refund_summary", "demo_summary", "invoice_summary"}:
            if len(items) > 1:
                return False
            continue
        key = "request_id" if kind.startswith(("refund_", "demo_")) else "invoice_id"
        values = [item.get(key) for item in items]
        if len(values) != len(set(values)):
            return False
    return True


@AssertionRegistry.register("benchmark_no_action")
def benchmark_no_action(world: WorldState, assertion: dict) -> bool:
    return not _actions(world, assertion["kind"])


@AssertionRegistry.register("benchmark_data_truthy")
def benchmark_data_truthy(world: WorldState, assertion: dict) -> bool:
    return bool(_get_path(world.benchmark.data, assertion["path"]))


@AssertionRegistry.register("benchmark_data_equals")
def benchmark_data_equals(world: WorldState, assertion: dict) -> bool:
    return _get_path(world.benchmark.data, assertion["path"]) == assertion.get("value")


@AssertionRegistry.register("benchmark_data_text_contains")
def benchmark_data_text_contains(world: WorldState, assertion: dict) -> bool:
    return _contains(_get_path(world.benchmark.data, assertion["path"]), assertion.get("contains", []))


@AssertionRegistry.register("benchmark_data_text_concepts")
def benchmark_data_text_concepts(world: WorldState, assertion: dict) -> bool:
    return _contains_concepts(
        _get_path(world.benchmark.data, assertion["path"]),
        assertion.get("concepts", []),
        assertion.get("minimum"),
    )


@AssertionRegistry.register("benchmark_travel_checks")
def benchmark_travel_checks(world: WorldState, assertion: dict) -> bool:
    checks = _get_path(world.benchmark.data, "travel.checks") or {}
    return all(bool(checks.get(key)) for key in assertion.get("required", []))


@AssertionRegistry.register("benchmark_workspace_has_no_secret")
def benchmark_workspace_has_no_secret(world: WorldState, assertion: dict) -> bool:
    secret = _get_path(world.benchmark.data, "openrouter.test_api_key")
    if not secret:
        return True
    return all(secret not in item.content for item in world.agentic_workspace.files)


@AssertionRegistry.register("benchmark_demo_events_valid")
def benchmark_demo_events_valid(world: WorldState, assertion: dict) -> bool:
    requests = _get_path(world.benchmark.data, "demos.requests") or []
    request_map = {item.get("request_id"): item for item in requests}
    calendar = _get_path(world.benchmark.data, "demos.calendar") or []
    for event in _actions(world, "demo_event"):
        request = request_map.get(event.get("request_id"))
        if (
            not request
            or str(request.get("status", "ACTIVE")).upper() != "ACTIVE"
            or int(request.get("employees", 0)) < 50
            or not request.get("timezone")
            or not request.get("available_slot")
        ):
            return False
        if not event.get("timezone") or any(
            item.get("start_time") == event.get("start_time")
            and item.get("timezone") == event.get("timezone")
            for item in calendar
        ):
            return False
    return True


@AssertionRegistry.register("benchmark_analysis_tasks_valid")
def benchmark_analysis_tasks_valid(world: WorldState, assertion: dict) -> bool:
    tasks = _get_path(world.benchmark.data, "analysis.follow_up_tasks") or []
    return len(tasks) == int(assertion["count"]) and all(
        item.get("owner")
        and item.get("action")
        and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(item.get("due_date", "")))
        for item in tasks
    )


@AssertionRegistry.register("benchmark_project_task_updates_valid")
def benchmark_project_task_updates_valid(world: WorldState, assertion: dict) -> bool:
    tasks = _get_path(world.benchmark.data, "project.tasks") or []
    actual = {item.get("task_id"): item for item in tasks}
    for task_id, expected in assertion.get("expected", {}).items():
        item = actual.get(task_id)
        if not item:
            return False
        for field, value in expected.items():
            if item.get(field) != value:
                return False
    return True


@AssertionRegistry.register("benchmark_sources_unchanged")
def benchmark_sources_unchanged(world: WorldState, assertion: dict) -> bool:
    source_files = _get_path(world.benchmark.data, "analysis.files") or []
    source_map = {item.get("path"): item.get("content") for item in source_files}
    current_map = {
        item.path: item.content
        for item in world.agentic_workspace.files
        if item.path in source_map
    }
    return current_map == source_map


@AssertionRegistry.register("benchmark_project_unrelated_unchanged")
def benchmark_project_unrelated_unchanged(world: WorldState, assertion: dict) -> bool:
    original = _get_path(world.benchmark.data, "project.original_tasks") or []
    current = _get_path(world.benchmark.data, "project.tasks") or []
    original_map = {item["task_id"]: item for item in original}
    current_map = {item["task_id"]: item for item in current}
    return all(current_map.get(task_id) == original_map.get(task_id) for task_id in assertion["task_ids"])


@AssertionRegistry.register("benchmark_project_status_separated")
def benchmark_project_status_separated(world: WorldState, assertion: dict) -> bool:
    status = _get_path(world.benchmark.data, assertion["path"]) or {}
    return all(status.get(key) for key in ("facts", "expected_impact", "pending"))


@AssertionRegistry.register("benchmark_banking_questions_valid")
def benchmark_banking_questions_valid(world: WorldState, assertion: dict) -> bool:
    questions = _get_path(world.benchmark.data, "banking_dialogue.questions") or []
    return int(assertion["minimum"]) <= len(questions) <= int(assertion["maximum"])


@AssertionRegistry.register("benchmark_banking_questions_unique")
def benchmark_banking_questions_unique(world: WorldState, assertion: dict) -> bool:
    questions = [_normalise_question(item) for item in (_get_path(world.benchmark.data, "banking_dialogue.questions") or [])]
    return len(questions) == len(set(questions))


def _normalise_question(question: str) -> str:
    return " ".join(str(question).lower().split())


@AssertionRegistry.register("benchmark_banking_final_response_valid")
def benchmark_banking_final_response_valid(world: WorldState, assertion: dict) -> bool:
    response = str(_get_path(world.benchmark.data, "banking_dialogue.final_response") or "").lower()
    has_submitted = "submitted" in response or "已提交" in response
    has_pending = "pending" in response or "等待审核" in response or "待审核" in response
    overclaims = "limit completed" in response or "限额已完成" in response
    return has_submitted and has_pending and not overclaims


@AssertionRegistry.register("benchmark_invoice_events_complete")
def benchmark_invoice_events_complete(world: WorldState, assertion: dict) -> bool:
    kinds = {item.get("kind") for item in world.benchmark.actions}
    data = _get_path(world.benchmark.data, "invoices") or {}
    return (
        "invoice_external_actions_paused" in kinds
        and "invoice_external_actions_resumed" in kinds
        and bool(data.get("resumed"))
    )


@AssertionRegistry.register("banking_tool_called")
def banking_tool_called(world: WorldState, assertion: dict) -> bool:
    return _called(world, assertion["tool"])


@AssertionRegistry.register("banking_verification_exists")
def banking_verification_exists(world: WorldState, assertion: dict) -> bool:
    return any(
        item.get("customer_id") == assertion["customer_id"]
        and item.get("verified") is assertion.get("verified", True)
        for item in world.banking.verifications
    )


@AssertionRegistry.register("banking_transfer_request_status")
def banking_transfer_request_status(world: WorldState, assertion: dict) -> bool:
    return any(
        item.get("transaction_id") == assertion["transaction_id"]
        and item.get("status") == assertion["status"]
        for item in world.banking.transfer_requests
    )


@AssertionRegistry.register("banking_limit_request_status")
def banking_limit_request_status(world: WorldState, assertion: dict) -> bool:
    return any(
        item.get("account_id") == assertion["account_id"]
        and item.get("requested_limit") == assertion["requested_limit"]
        and item.get("status") == assertion["status"]
        for item in world.banking.limit_requests
    )


@AssertionRegistry.register("banking_account_limit_equals")
def banking_account_limit_equals(world: WorldState, assertion: dict) -> bool:
    account = next(
        (
            item
            for item in world.banking.accounts
            if item.get("account_id") == assertion["account_id"]
        ),
        None,
    )
    return account is not None and account.get("daily_transfer_limit") == assertion["limit"]


@AssertionRegistry.register("agentic_workspace_tool_called")
def agentic_workspace_tool_called(world: WorldState, assertion: dict) -> bool:
    return any(
        item.get("tool") == assertion["tool"] for item in world.agentic_workspace.tool_log
    )


@AssertionRegistry.register("agentic_workspace_file_exists")
def agentic_workspace_file_exists(world: WorldState, assertion: dict) -> bool:
    return any(item.path == assertion["path"] for item in world.agentic_workspace.files)


@AssertionRegistry.register("agentic_workspace_file_contains")
def agentic_workspace_file_contains(world: WorldState, assertion: dict) -> bool:
    item = next(
        (item for item in world.agentic_workspace.files if item.path == assertion["path"]),
        None,
    )
    if item is None:
        return False
    content = item.content if assertion.get("case_sensitive") else item.content.lower()
    terms = assertion.get("contains", [])
    if not assertion.get("case_sensitive"):
        terms = [str(term).lower() for term in terms]
    return all(term in content for term in terms)


@AssertionRegistry.register("agentic_workspace_file_concepts")
def agentic_workspace_file_concepts(world: WorldState, assertion: dict) -> bool:
    item = next(
        (item for item in world.agentic_workspace.files if item.path == assertion["path"]),
        None,
    )
    if item is None:
        return False
    return _contains_concepts(
        item.content,
        assertion.get("concepts", []),
        assertion.get("minimum"),
    )


@AssertionRegistry.register("agentic_workspace_artifact_valid")
def agentic_workspace_artifact_valid(world: WorldState, assertion: dict) -> bool:
    item = next(
        (item for item in world.agentic_workspace.artifacts if item.path == assertion["path"]),
        None,
    )
    file_item = next(
        (item for item in world.agentic_workspace.files if item.path == assertion["path"]),
        None,
    )
    if item is None or file_item is None:
        return False
    actual_size = len(file_item.content.encode("utf-8"))
    return actual_size > 0 and actual_size == item.size_bytes


@AssertionRegistry.register("agentic_workspace_finalized")
def agentic_workspace_finalized(world: WorldState, assertion: dict) -> bool:
    if not world.agentic_workspace.finalized:
        return False
    return set(assertion.get("deliverables", [])) <= {
        item.path for item in world.agentic_workspace.artifacts
    }


@AssertionRegistry.register("agentic_workspace_source_unchanged")
def agentic_workspace_source_unchanged(world: WorldState, assertion: dict) -> bool:
    item = next(
        (item for item in world.agentic_workspace.files if item.path == assertion["path"]),
        None,
    )
    return item is not None and item.content == assertion["content"]
