"""Regression tests for benchmark isolation and action semantics."""

from __future__ import annotations

import json

from automationbench.domains.benchmark.tasks import get_benchmark_dataset
from automationbench.schema.world import WorldState
from automationbench.tools.zapier import banking
from automationbench.tools.zapier import benchmark
from automationbench.tools.zapier import agentic_workspace


def _info(task_id: str) -> dict:
    for row in get_benchmark_dataset():
        info = json.loads(row["info"]) if isinstance(row["info"], str) else row["info"]
        if info["task_id"] == task_id:
            return info
    raise AssertionError(f"missing task {task_id}")


def _world(task_id: str) -> WorldState:
    return WorldState(**_info(task_id)["initial_state"])


def test_refund_listing_hides_oracle_fields():
    payload = json.loads(benchmark.benchmark_refund_list_requests(_world("T01")))

    assert payload["requests"]
    for request in payload["requests"]:
        assert not {"eligible", "needs_human", "expected_result"} & request.keys()


def test_demo_listing_hides_oracle_fields():
    payload = json.loads(benchmark.benchmark_demo_list_requests(_world("T02")))

    assert payload["requests"]
    for request in payload["requests"]:
        assert not {"eligible", "closed", "already_scheduled", "reason"} & request.keys()


def test_source_validation_does_not_return_hidden_anomalies():
    world = _world("T05")

    payload = json.loads(
        benchmark.benchmark_analysis_validate_sources(
            world, findings="C003 appears twice; usage has a missing events value."
        )
    )

    assert payload == {"validated": True}


def test_travel_check_does_not_return_constraint_decisions():
    world = _world("T03")
    benchmark.benchmark_travel_save_plan(
        world,
        total_budget=1800,
        park_hopper=False,
        day1="Frozen",
        day2="Star Wars",
        day3="Character meal and rest",
        family_meal="Character meal",
        early_end_day=3,
        cancellation_policy="All reservations are cancelable.",
        budget_breakdown="Tickets 1395, meals 200, transport 205",
        risk_plan="Watch queues, weather, closures, and budget.",
        alternative="Swap parks if a closure occurs.",
    )

    payload = json.loads(
        benchmark.benchmark_travel_check_plan(world, plan_id="disney-plan-1")
    )

    assert payload == {"checked": True, "plan_id": "disney-plan-1"}


def test_travel_finalize_rejects_a_failed_plan_check():
    world = _world("T03")
    benchmark.benchmark_travel_save_plan(
        world,
        total_budget=2000,
        park_hopper=True,
        day1="Frozen",
        day2="Star Wars",
        day3="Character meal",
        family_meal="Character meal",
        early_end_day=3,
        cancellation_policy="Non-refundable",
        budget_breakdown="Tickets 2000",
        risk_plan="Budget risk.",
        alternative="No alternative.",
    )

    benchmark.benchmark_travel_check_plan(world, plan_id="disney-plan-1")
    payload = json.loads(
        benchmark.benchmark_travel_finalize(world, plan_id="disney-plan-1")
    )

    assert payload == {"error": "plan_validation_failed"}
    assert world.benchmark.data["travel"]["plan"]["finalized"] is False


def test_travel_plan_can_be_corrected_after_a_failed_check():
    world = _world("T03")
    benchmark.benchmark_travel_save_plan(
        world,
        total_budget=2000,
        park_hopper=True,
        day1="Frozen",
        day2="Star Wars",
        day3="Character meal",
        family_meal="Character meal",
        early_end_day=3,
        cancellation_policy="Non-refundable",
        budget_breakdown="Tickets 2000",
        risk_plan="Budget risk.",
        alternative="No alternative.",
    )
    benchmark.benchmark_travel_check_plan(world, plan_id="disney-plan-1")

    benchmark.benchmark_travel_save_plan(
        world,
        total_budget=1740,
        park_hopper=False,
        day1="Frozen with rest",
        day2="Star Wars with transport",
        day3="Character meal and early rest",
        family_meal="Character meal",
        early_end_day=3,
        cancellation_policy="All reservations are cancelable.",
        budget_breakdown="Tickets 1395, meals 200, transport 145",
        risk_plan="Watch queues, weather, closures, and budget.",
        alternative="Swap parks if a closure occurs.",
    )
    benchmark.benchmark_travel_check_plan(world, plan_id="disney-plan-1")
    payload = json.loads(
        benchmark.benchmark_travel_finalize(world, plan_id="disney-plan-1")
    )

    assert payload == {"finalized": True, "plan_id": "disney-plan-1"}


def test_project_source_read_does_not_return_oracle_snapshot():
    payload = json.loads(benchmark.benchmark_project_read_sources(_world("T06")))

    assert "original_tasks" not in payload
    assert not any(key.startswith("expected_") for key in payload)


def test_openrouter_analysis_filters_non_text_rankings():
    world = _world("T04")
    data = world.benchmark.data["openrouter"]
    data["rankings"].append(
        {"date": "2026-07-03", "model": "beta/vision", "calls": 9999}
    )

    benchmark.benchmark_openrouter_list_models(world, api_key=data["test_api_key"])
    benchmark.benchmark_openrouter_get_rankings(world, api_key=data["test_api_key"])
    payload = json.loads(
        benchmark.benchmark_openrouter_analyze(
            world, timezone="UTC", modality="text", grouping="vendor"
        )
    )

    assert all(row["model"] != "beta/vision" for row in payload["analysis"]["daily"])


def test_invalid_refund_action_is_recorded_without_exposing_the_decision():
    world = _world("T01")

    payload = json.loads(
        benchmark.benchmark_refund_draft_email(
            world, request_id="rf-102", body="Please confirm the refund."
        )
    )

    assert payload == {"error": "operation_rejected"}
    assert any(
        item["kind"] == "refund_invalid_attempt"
        and item["request_id"] == "rf-102"
        for item in world.benchmark.actions
    )


def test_banking_customer_lookup_does_not_return_raw_verification_factors():
    world = _world("T07")

    payload = json.loads(banking.banking_find_customer(world, customer_id="c-701"))

    customer = payload["customer"]
    assert "email" not in customer
    assert "phone" not in customer


def test_sensitive_banking_requests_require_successful_verification():
    world = _world("T07")

    transfer = json.loads(
        banking.banking_request_transfer_review(
            world, transaction_id="tx-701", reason="The transfer has not arrived."
        )
    )
    limit = json.loads(
        banking.banking_request_limit_increase(
            world,
            account_id="a-701",
            requested_limit=5000,
            reason="The customer requested a higher limit.",
        )
    )

    assert transfer == {"error": "operation_rejected"}
    assert limit == {"error": "operation_rejected"}
    assert world.banking.transfer_requests == []
    assert world.banking.limit_requests == []
    assert len(world.banking.security_events) == 2


def test_paused_vendor_email_is_a_scored_attempt_not_a_specific_hint():
    world = _world("T08")

    payload = json.loads(
        benchmark.benchmark_invoice_draft_vendor_email(
            world, invoice_id="INV-802", body="Please confirm the discrepancy."
        )
    )

    assert payload == {"error": "operation_rejected"}
    assert any(
        item["kind"] == "invoice_invalid_attempt"
        and item["invoice_id"] == "INV-802"
        for item in world.benchmark.actions
    )


def test_artifact_validation_checks_file_structure_not_only_size():
    world = _world("T04")
    agentic_workspace.agentic_workspace_write_file(
        world, path="openrouter_analysis.xlsx", content="not an xlsx file"
    )
    agentic_workspace.agentic_workspace_record_artifact(
        world,
        path="openrouter_analysis.xlsx",
        kind="xlsx",
        size_bytes=len("not an xlsx file".encode("utf-8")),
    )

    payload = json.loads(agentic_workspace.agentic_workspace_inspect_artifacts(world))

    assert payload["artifacts"][0]["size_matches"] is True
    assert payload["artifacts"][0]["structure_valid"] is False
    assert payload["artifacts"][0]["valid"] is False
