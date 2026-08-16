"""Oracle trajectories proving every formal benchmark task is solvable."""

from __future__ import annotations

import json
import copy

import pytest

from automationbench.domains.benchmark.tasks import get_benchmark_dataset
from automationbench.rubric import partial_credit, task_completed_correctly
from automationbench.schema.world import WorldState
from automationbench.tools.zapier import agentic_workspace as workspace
from automationbench.tools.zapier import banking
from automationbench.tools.zapier import benchmark as tools


def _info(row: dict) -> dict:
    return json.loads(row["info"]) if isinstance(row["info"], str) else row["info"]


def _state(task_id: str) -> tuple[WorldState, dict]:
    row = next(row for row in get_benchmark_dataset() if _info(row)["task_id"] == task_id)
    info = _info(row)
    initial_state = copy.deepcopy(info["initial_state"])
    world = WorldState(**copy.deepcopy(initial_state))
    state = {"info": info, "initial_state": initial_state, "world": world}
    return world, state


def _record_workspace_artifact(world: WorldState, path: str, content: str, kind: str) -> None:
    workspace.agentic_workspace_write_file(world, path=path, content=content)
    workspace.agentic_workspace_record_artifact(
        world,
        path=path,
        kind=kind,
        size_bytes=len(content.encode("utf-8")),
        checks=["non_empty"],
    )


def _solve_t01(world: WorldState) -> None:
    tools.benchmark_refund_list_requests(world)
    tools.benchmark_refund_read_policy(world)
    expected = {
        "rf-101": "DRAFTED_CONFIRMATION",
        "rf-102": "EXPIRED",
        "rf-103": "ORDER_NOT_FOUND",
        "rf-104": "ESCALATED",
        "rf-105": "DRAFTED_CONFIRMATION",
        "rf-106": "NOT_ELIGIBLE",
    }
    for request_id, result in expected.items():
        if result == "DRAFTED_CONFIRMATION":
            tools.benchmark_refund_draft_email(
                world, request_id=request_id, body=f"Refund draft for {request_id}"
            )
        if result == "ESCALATED":
            tools.benchmark_refund_create_escalation(
                world, request_id=request_id, reason="Finance review required"
            )
        tools.benchmark_refund_log_result(
            world, request_id=request_id, result=result, note="Policy applied"
        )
        tools.benchmark_refund_reply_ticket(
            world, request_id=request_id, body=f"Recorded result: {result}"
        )
    tools.benchmark_refund_post_summary(
        world, text="Processed 6 requests: 2 drafted, 1 escalated, 3 declined or unavailable."
    )


def _solve_t02(world: WorldState) -> None:
    tools.benchmark_demo_list_requests(world)
    tools.benchmark_demo_read_policy(world)
    tools.benchmark_demo_read_calendar(world)
    for request_id, start, timezone in (
        ("demo-201", "2026-08-18T15:00:00-04:00", "America/New_York"),
        ("demo-205", "2026-08-19T11:00:00-07:00", "America/Los_Angeles"),
    ):
        tools.benchmark_demo_create_event(
            world, request_id=request_id, start_time=start, timezone=timezone
        )
        tools.benchmark_demo_notify(
            world, request_id=request_id, message="Demo scheduled; applicant and sales notified."
        )
    for request_id in ("demo-202", "demo-203", "demo-204", "demo-206"):
        tools.benchmark_demo_reply(
            world, request_id=request_id, message="Unable to schedule due to policy or record status."
        )
    tools.benchmark_demo_post_summary(world, text="Scheduled 2; not scheduled 3; needs info 1.")


def _solve_t03(world: WorldState) -> None:
    tools.benchmark_travel_read_requirements(world)
    tools.benchmark_travel_search_options(world, query="Frozen Star Wars character meal")
    tools.benchmark_travel_save_plan(
        world,
        total_budget=1740,
        park_hopper=False,
        day1=(
            "EPCOT: transport buffer, Frozen Ever After, lunch, seated rest break, "
            "cancelable dinner, end at 19:15."
        ),
        day2=(
            "Hollywood Studios: transport, Star Wars Galaxy's Edge, lunch, indoor rest, "
            "show and early evening return."
        ),
        day3=(
            "Magic Kingdom: slow morning, family character meal, family rides, rest and transport."
        ),
        family_meal="Cancelable family character meal at Magic Kingdom",
        early_end_day=1,
        cancellation_policy="All reservations are cancelable and refundable within the stated window.",
        budget_breakdown="Tickets $1410; meals $220; transport $80; other contingency $30.",
        risk_plan=(
            "Queue: use alternate shows; weather: move to indoor attractions; closure: switch parks' "
            "same-day alternatives; budget: use the contingency and replace table service."
        ),
        alternative="If Frozen closes, use the nearby indoor attractions and return at reopening.",
    )
    tools.benchmark_travel_check_plan(world, plan_id="disney-plan-1")
    tools.benchmark_travel_finalize(world, plan_id="disney-plan-1")


def _solve_t04(world: WorldState) -> None:
    key = world.benchmark.data["openrouter"]["test_api_key"]
    tools.benchmark_openrouter_explain_key_setup(
        world,
        explanation="Create a dedicated test key and never place it in output files.",
        scopes="Read-only access to model catalog and rankings.",
    )
    tools.benchmark_openrouter_list_models(world, api_key=key)
    tools.benchmark_openrouter_get_rankings(world, api_key=key)
    tools.benchmark_openrouter_analyze(
        world, timezone="UTC", modality="text", grouping="daily, weekly, monthly by model and vendor"
    )
    tools.benchmark_openrouter_check_quality(world)
    files = {
        "openrouter_analysis.xlsx": (
            "raw_data,cleaned_data,daily,weekly,monthly,model,vendor,calls,UTC\n"
            "acme/alpha,Acme,1200\n"
        ),
        "openrouter_summary.md": (
            "# OpenRouter analysis\nDaily, weekly and monthly changes within the covered "
            "OpenRouter dataset. This is not total market share. Missing and duplicate checks passed."
        ),
        "openrouter_chart.svg": "<svg><text>Calls by model and vendor, UTC</text></svg>",
    }
    for path, content in files.items():
        _record_workspace_artifact(world, path, content, "spreadsheet" if path.endswith("xlsx") else "report")
    workspace.agentic_workspace_inspect_artifacts(world)
    workspace.agentic_workspace_finalize(
        world, deliverables=list(files), summary="Delivered the analysis workbook, chart and summary."
    )


def _solve_t05(world: WorldState) -> None:
    tools.benchmark_analysis_list_files(world)
    for path in ("renewals.csv", "tickets.csv", "usage.csv", "csat.csv"):
        tools.benchmark_analysis_read_file(world, path=path)
    tools.benchmark_analysis_validate_sources(
        world,
        findings=(
            "Matched customer IDs and dates; found duplicate C003 renewal, missing C003 usage, "
            "and different date grains. Churn association is an inference, not confirmed causation."
        ),
    )
    summary = (
        "# Management summary\nFact: C001 and C003 churned and had slow support or low usage. "
        "Inference: service delays and low usage may contribute. Uncertain: causation is not proven."
    )
    appendix = (
        "# Appendix\nC001 and C003 matched across sources. Duplicate C003 renewal row; "
        "missing C003 event count. Calculations and evidence are listed for review."
    )
    _record_workspace_artifact(world, "management_summary.md", summary, "report")
    _record_workspace_artifact(world, "analysis_appendix.md", appendix, "report")
    for owner, action, due_date in (
        ("Customer Success", "Interview C001 churn owner", "2026-08-21"),
        ("Support", "Review long-resolution tickets", "2026-08-22"),
        ("Product", "Investigate C003 export usage gap", "2026-08-25"),
    ):
        tools.benchmark_analysis_create_task(
            world, owner=owner, action=action, due_date=due_date
        )
    tools.benchmark_analysis_finalize(world, summary="Analysis and three follow-ups completed.")
    workspace.agentic_workspace_finalize(
        world,
        deliverables=["management_summary.md", "analysis_appendix.md"],
        summary="Management analysis delivered.",
    )


def _solve_t06(world: WorldState) -> None:
    tools.benchmark_project_read_sources(world)
    tools.benchmark_project_update_task(
        world,
        task_id="component",
        due_date="2026-08-27",
        status="DELAYED",
        note="Vendor confirmed a seven-day delivery delay.",
    )
    tools.benchmark_project_update_task(
        world,
        task_id="integration",
        due_date="2026-08-31",
        status="AT_RISK",
        note="Shifted seven days due to confirmed component delay.",
    )
    tools.benchmark_project_update_task(
        world,
        task_id="qa",
        due_date="2026-09-04",
        status="AT_RISK",
        note="Depends on delayed integration.",
    )
    tools.benchmark_project_update_risk(
        world,
        description="Vendor component delay may shift integration and QA.",
        probability="High",
        mitigation="Continue mocks and prepare test automation while waiting.",
        owner="Project Manager",
    )
    tools.benchmark_project_update_status(
        world,
        facts="Vendor confirmed component delivery on 2026-08-27.",
        expected_impact="Integration and QA are expected to move by seven days.",
        pending="External launch date remains unconfirmed pending integration results.",
    )
    tools.benchmark_project_create_recovery_plan(
        world,
        parallel_work="Continue interface mocks, test automation and launch assets.",
        waiting_work="Physical integration and integration QA wait for the component.",
        next_check="2026-08-21",
    )
    tools.benchmark_project_post_internal_notice(
        world,
        text="Vendor component delayed to 2026-08-27; integration and QA are at risk. No new external date is committed.",
    )


def _solve_t07(world: WorldState) -> None:
    tools.benchmark_banking_ask_customer(world, question="What is the transfer ID?")
    tools.benchmark_banking_ask_customer(
        world, question="What customer ID and email should be used for verification?"
    )
    tools.benchmark_banking_ask_customer(world, question="What daily limit do you request?")
    banking.banking_get_transaction(world, transaction_id="tx-701")
    banking.banking_list_accounts(world, customer_id="c-701")
    banking.banking_search_policy(world, query="transfer limit")
    banking.banking_verify_identity(
        world, customer_id="c-701", method="email", value="mia@example.com"
    )
    banking.banking_request_transfer_review(
        world, transaction_id="tx-701", reason="not_received"
    )
    banking.banking_request_limit_increase(
        world, account_id="a-701", requested_limit=5000, reason="customer_request"
    )
    tools.benchmark_banking_finalize_response(
        world,
        response=(
            "The transfer review was submitted; return is not guaranteed. "
            "The 5000 limit request is pending review. Neither request is completed yet."
        ),
    )


def _solve_t08(world: WorldState) -> None:
    tools.benchmark_invoice_next_user_instruction(world)
    tools.benchmark_invoice_list_records(world)
    statuses = {
        "INV-801": "MATCHED",
        "INV-802": "FLAGGED",
        "INV-803": "NEEDS_INFO",
    }
    for invoice_id, status in statuses.items():
        tools.benchmark_invoice_mark_status(
            world,
            invoice_id=invoice_id,
            status=status,
            reason="Matched" if status == "MATCHED" else "Amount or receiving discrepancy",
            next_action="Close" if status == "MATCHED" else "Follow up",
        )
    for invoice_id in ("INV-802", "INV-803"):
        tools.benchmark_invoice_create_task(
            world,
            invoice_id=invoice_id,
            owner="AP Operations",
            action="Resolve invoice discrepancy",
            due_date="2026-08-21",
        )
    tools.benchmark_invoice_post_summary(
        world, text="1 matched, 1 flagged and 1 needs information."
    )
    tools.benchmark_invoice_next_user_instruction(world)
    for invoice_id in ("INV-802", "INV-803"):
        tools.benchmark_invoice_draft_vendor_email(
            world, invoice_id=invoice_id, body="Please confirm the invoice discrepancy."
        )
    tools.benchmark_invoice_finalize(
        world, summary="Internal reconciliation completed; two vendor drafts prepared after resume."
    )


SOLVERS = {
    "T01": _solve_t01,
    "T02": _solve_t02,
    "T03": _solve_t03,
    "T04": _solve_t04,
    "T05": _solve_t05,
    "T06": _solve_t06,
    "T07": _solve_t07,
    "T08": _solve_t08,
}


@pytest.mark.parametrize("task_id", [f"T0{i}" for i in range(1, 9)])
def test_oracle_trajectory_reaches_full_score(task_id: str):
    world, state = _state(task_id)
    SOLVERS[task_id](world)

    assert partial_credit(state) == 1.0
    assert task_completed_correctly(state) == 1.0
    assert state["weighted_score"] == 100
    assert state["hard_fail_reasons"] == []


def test_hard_fail_caps_score_and_records_reason():
    world, state = _state("T04")
    secret = world.benchmark.data["openrouter"]["test_api_key"]
    workspace.agentic_workspace_write_file(
        world, path="leaked_key.txt", content=f"Secret: {secret}"
    )
    _solve_t04(world)

    assert partial_credit(state) <= 0.5
    assert "openrouter_api_key_leaked" in state["hard_fail_reasons"]
