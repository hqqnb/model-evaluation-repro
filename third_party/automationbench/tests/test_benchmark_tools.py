"""Tests for benchmark-inspired banking and bounded workspace tools."""

from __future__ import annotations

import json

from automationbench.schema.world import WorldState
from automationbench.schema.agentic_workspace import AgenticWorkspaceState, WorkspaceFile
from automationbench.schema.banking import BankingState
from automationbench.tools import ALL_TOOLS
from automationbench.tools.api.fetch import api_fetch
from automationbench.tools.api.search import api_search
from automationbench.tools.zapier.agentic_workspace import (
    agentic_workspace_finalize,
    agentic_workspace_inspect_artifacts,
    agentic_workspace_list_files,
    agentic_workspace_read_file,
    agentic_workspace_record_artifact,
    agentic_workspace_run_python,
    agentic_workspace_write_file,
)
from automationbench.tools.zapier.banking import (
    banking_find_customer,
    banking_get_transaction,
    banking_list_accounts,
    banking_request_limit_increase,
    banking_request_transfer_review,
    banking_search_policy,
    banking_transfer_to_human,
    banking_verify_identity,
)
from automationbench.tools.zapier.benchmark import (
    benchmark_travel_check_plan,
    benchmark_travel_save_plan,
)


def make_banking_world() -> WorldState:
    return WorldState(
        banking=BankingState(
            customers=[
                {
                    "customer_id": "c1",
                    "name": "Mia Smith",
                    "email": "mia@example.com",
                    "phone": "512-555-0147",
                }
            ],
            accounts=[
                {
                    "account_id": "a1",
                    "customer_id": "c1",
                    "status": "OPEN",
                    "daily_transfer_limit": 1000,
                }
            ],
            transactions=[
                {
                    "transaction_id": "tx1",
                    "account_id": "a1",
                    "customer_id": "c1",
                    "type": "INTERNATIONAL_TRANSFER",
                    "status": "PENDING",
                    "amount": 250,
                }
            ],
            policies=[
                {
                    "policy_id": "p1",
                    "topic": "transfers",
                    "text": "Pending international transfers may be submitted for review.",
                }
            ],
        )
    )


def make_workspace_world() -> WorldState:
    return WorldState(
        agentic_workspace=AgenticWorkspaceState(
            files=[
                WorkspaceFile(
                    path="input.csv",
                    content="name,value\nA,1\n",
                    mime_type="text/csv",
                )
            ],
            artifacts=[],
        )
    )


def test_world_accepts_benchmark_states():
    banking_world = make_banking_world()
    workspace_world = make_workspace_world()

    assert banking_world.banking.customers[0]["customer_id"] == "c1"
    assert banking_world.banking.transactions[0]["status"] == "PENDING"
    assert workspace_world.agentic_workspace.files[0].path == "input.csv"


def test_banking_tools_query_policy_and_verify_identity():
    world = make_banking_world()

    customer = json.loads(banking_find_customer(world, customer_id="c1"))
    accounts = json.loads(banking_list_accounts(world, customer_id="c1"))
    transaction = json.loads(banking_get_transaction(world, transaction_id="tx1"))
    policy = json.loads(banking_search_policy(world, query="transfer"))
    verified = json.loads(
        banking_verify_identity(
            world, customer_id="c1", method="email", value="mia@example.com"
        )
    )

    assert customer["customer"]["customer_id"] == "c1"
    assert accounts["accounts"][0]["account_id"] == "a1"
    assert transaction["transaction"]["status"] == "PENDING"
    assert policy["results"][0]["policy_id"] == "p1"
    assert verified["verified"] is True
    assert world.banking.verifications[0]["customer_id"] == "c1"


def test_banking_tools_create_review_requests_without_claiming_completion():
    world = make_banking_world()

    banking_verify_identity(
        world, customer_id="c1", method="email", value="mia@example.com"
    )
    transfer = json.loads(
        banking_request_transfer_review(world, transaction_id="tx1", reason="not_received")
    )
    limit = json.loads(
        banking_request_limit_increase(
            world, account_id="a1", requested_limit=5000, reason="travel"
        )
    )

    assert transfer["status"] == "SUBMITTED"
    assert limit["status"] == "PENDING_REVIEW"
    assert world.banking.transfer_requests[0]["transaction_id"] == "tx1"
    assert world.banking.limit_requests[0]["requested_limit"] == 5000


def test_banking_transfer_to_human_records_handoff():
    world = make_banking_world()

    result = json.loads(
        banking_transfer_to_human(world, reason="customer_requests_human", summary="Needs review")
    )

    assert result["transferred"] is True
    assert world.banking.handoffs[0]["reason"] == "customer_requests_human"


def test_workspace_can_list_read_and_write_files():
    world = make_workspace_world()

    listing = json.loads(agentic_workspace_list_files(world))
    content = json.loads(agentic_workspace_read_file(world, path="input.csv"))
    written = json.loads(
        agentic_workspace_write_file(world, path="summary.md", content="# Summary")
    )

    assert listing["files"][0]["path"] == "input.csv"
    assert content["content"].startswith("name")
    assert written["created"] is True
    assert any(item.path == "summary.md" for item in world.agentic_workspace.files)


def test_workspace_runs_bounded_python_against_virtual_files():
    world = make_workspace_world()

    result = json.loads(
        agentic_workspace_run_python(
            world,
            source=(
                "rows = read_file('input.csv').splitlines()\n"
                "write_file('count.txt', str(len(rows) - 1))\n"
            ),
        )
    )

    assert result["ok"] is True
    assert result["stdout"] == ""
    assert json.loads(agentic_workspace_read_file(world, path="count.txt"))["content"] == "1"


def test_workspace_rejects_python_imports_and_path_escape():
    world = make_workspace_world()

    result = json.loads(
        agentic_workspace_run_python(world, source="import os\nprint(os.listdir('.'))")
    )

    assert result["ok"] is False
    assert result["error"] == "unsafe_code"


def test_workspace_rejects_path_escape_and_records_artifact_metadata():
    world = make_workspace_world()

    error = json.loads(agentic_workspace_read_file(world, path="../secret.txt"))
    agentic_workspace_write_file(world, path="summary.md", content="# Summary")
    recorded = json.loads(
        agentic_workspace_record_artifact(
            world, path="summary.md", kind="text", size_bytes=9, checks=["non_empty"]
        )
    )
    report = json.loads(agentic_workspace_inspect_artifacts(world))

    assert error["error"] == "invalid_path"
    assert recorded["recorded"] is True
    assert report["artifacts"][0]["path"] == "summary.md"
    assert report["artifacts"][0]["size_bytes"] == 9


def test_workspace_finalize_returns_selected_deliverables():
    world = make_workspace_world()
    agentic_workspace_write_file(world, path="summary.md", content="# Summary")
    agentic_workspace_record_artifact(
        world, path="summary.md", kind="text", size_bytes=9, checks=["non_empty"]
    )

    result = json.loads(
        agentic_workspace_finalize(
            world, deliverables=["summary.md"], summary="Created the summary."
        )
    )

    assert result["finalized"] is True
    assert result["deliverables"] == ["summary.md"]
    assert world.agentic_workspace.finalized is True


def test_benchmark_tools_are_registered_for_direct_tool_mode():
    names = {tool.__name__ for tool in ALL_TOOLS}

    assert "banking_search_policy" in names
    assert "banking_request_transfer_review" in names
    assert "agentic_workspace_read_file" in names
    assert "agentic_workspace_finalize" in names


def test_travel_check_accepts_chinese_pacing_and_cancelable_policy():
    world = WorldState(benchmark={"task_id": "T03", "data": {"travel": {}}})
    benchmark_travel_save_plan(
        world,
        total_budget=1740,
        park_hopper=False,
        day1="EPCOT：Frozen，安排交通缓冲、午餐和室内休息。",
        day2="Hollywood Studios：Star Wars，安排餐食和慢节奏休息。",
        day3="Magic Kingdom：全家角色主题用餐，19:00 前结束。",
        family_meal="Magic Kingdom 全家角色主题用餐",
        early_end_day=3,
        cancellation_policy="只采用可取消预订，不采用任何不可取消预订。",
        budget_breakdown="三个园区一日票、餐食和交通合计 1740 美元。",
        risk_plan="天气、排队、项目停运和预算均有替代方案。",
        alternative="项目停运时改为同园区室内项目。",
    )

    result = json.loads(
        benchmark_travel_check_plan(world, plan_id="disney-plan-1")
    )

    assert result == {"checked": True, "plan_id": "disney-plan-1"}
    assert all(world.benchmark.data["travel"]["checks"].values())


def test_benchmark_tools_are_discoverable_through_api_mode():
    banking_search = json.loads(api_search("banking transfer policy", top_k=10))
    workspace_search = json.loads(api_search("workspace artifact file", top_k=10))

    banking_ids = {item["id"] for item in banking_search["results"]}
    workspace_ids = {item["id"] for item in workspace_search["results"]}

    assert "benchmark_banking.policies.search" in banking_ids
    assert "benchmark_workspace.files.get" in workspace_ids


def test_benchmark_banking_api_route_mutates_world():
    world = make_banking_world()

    banking_verify_identity(
        world, customer_id="c1", method="email", value="mia@example.com"
    )
    result = json.loads(
        api_fetch(
            world,
            method="POST",
            url="https://banking.benchmark.local/v1/transfers/tx1/review",
            body=json.dumps({"reason": "not_received"}),
        )
    )

    assert result["status"] == "SUBMITTED"
    assert world.banking.transfer_requests[0]["transaction_id"] == "tx1"


def test_benchmark_workspace_api_route_reads_and_writes_virtual_files():
    world = make_workspace_world()

    read_result = json.loads(
        api_fetch(
            world,
            method="GET",
            url="https://workspace.benchmark.local/v1/files/input.csv",
        )
    )
    write_result = json.loads(
        api_fetch(
            world,
            method="POST",
            url="https://workspace.benchmark.local/v1/files",
            body=json.dumps({"path": "summary.md", "content": "# Summary"}),
        )
    )

    assert read_result["content"].startswith("name")
    assert write_result["created"] is True
