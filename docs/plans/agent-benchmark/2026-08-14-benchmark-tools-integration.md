# Benchmark Tools Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small, stateful banking toolset inspired by tau3-bench and a bounded artifact/workspace toolset inspired by GDPval-style agentic sandboxes to AutomationBench.

**Architecture:** Add two optional services to `WorldState`: `banking` and `agentic_workspace`. Expose their operations as direct tools so they work with the existing `limited_zapier` and meta-tool runner modes. Keep all state local and deterministic; use task assertions and partial credit rather than external network calls or teacher-only grading.

**Tech Stack:** Python 3.13, Pydantic 2, existing AutomationBench tool registration, pytest.

---

### Task 1: Add the banking state model

**Files:**
- Create: `third_party/automationbench/automationbench/schema/banking.py`
- Modify: `third_party/automationbench/automationbench/schema/world.py`
- Test: `third_party/automationbench/tests/test_benchmark_tools.py`

- [ ] **Step 1: Write the failing state construction test**

```python
def test_world_accepts_banking_state():
    world = WorldState(
        banking={
            "customers": [{"customer_id": "c1", "name": "Mia"}],
            "accounts": [{"account_id": "a1", "customer_id": "c1", "status": "OPEN"}],
            "transactions": [{"transaction_id": "tx1", "status": "PENDING"}],
            "policies": [{"policy_id": "p1", "topic": "transfers", "text": "Pending transfers may be reviewed."}],
        }
    )
    assert world.banking.customers[0]["customer_id"] == "c1"
    assert world.banking.transactions[0]["status"] == "PENDING"
```

- [ ] **Step 2: Run the test and verify it fails because `WorldState` has no banking field**

Run: `cd third_party/automationbench && pytest tests/test_benchmark_tools.py::test_world_accepts_banking_state -q`

Expected: FAIL with a Pydantic validation error for the missing `banking` field or an import error for the missing schema.

- [ ] **Step 3: Implement the minimal Pydantic state**

Create a `BankingState` with list-backed records for customers, accounts, transactions, policy documents, verification records, transfer requests, limit requests, and transfer records. Use `extra="forbid"` and a `tool_log` list so unknown task data is rejected instead of silently ignored.

- [ ] **Step 4: Add `banking: BankingState` to `WorldState`**

Import the schema and add it next to the other service fields with an empty default.

- [ ] **Step 5: Run the focused test and then the world-state tests**

Run: `cd third_party/automationbench && pytest tests/test_benchmark_tools.py::test_world_accepts_banking_state tests/test_domains.py -q`

Expected: PASS.

### Task 2: Add tau3-inspired banking tools

**Files:**
- Create: `third_party/automationbench/automationbench/tools/zapier/banking.py`
- Modify: `third_party/automationbench/automationbench/tools/__init__.py`
- Test: `third_party/automationbench/tests/test_benchmark_tools.py`

- [ ] **Step 1: Write failing tests for read and state-changing behavior**

Cover:

```python
def test_banking_tools_query_policy_and_verify_identity():
    world = make_banking_world()
    result = json.loads(banking_search_policy(world, query="transfer"))
    assert result["results"][0]["policy_id"] == "p1"
    verified = json.loads(banking_verify_identity(world, customer_id="c1", method="email", value="mia@example.com"))
    assert verified["verified"] is True

def test_banking_tools_create_review_requests_without_claiming_completion():
    world = make_banking_world()
    transfer = json.loads(banking_request_transfer_review(world, transaction_id="tx1", reason="not_received"))
    assert transfer["status"] == "SUBMITTED"
    limit = json.loads(banking_request_limit_increase(world, account_id="a1", requested_limit=5000, reason="travel"))
    assert limit["status"] == "PENDING_REVIEW"
    assert len(world.banking.transfer_requests) == 1
    assert len(world.banking.limit_requests) == 1
```

- [ ] **Step 2: Run the focused tests and confirm the tools are missing**

Run: `cd third_party/automationbench && pytest tests/test_benchmark_tools.py -q`

Expected: FAIL with import errors for the new banking tool functions.

- [ ] **Step 3: Implement deterministic banking operations**

Implement:

- `banking_find_customer`
- `banking_list_accounts`
- `banking_get_transaction`
- `banking_search_policy`
- `banking_verify_identity`
- `banking_request_transfer_review`
- `banking_request_limit_increase`
- `banking_transfer_to_human`

Read tools must return bounded JSON and log the call. Write tools must validate identifiers, preserve `SUBMITTED` versus `COMPLETED`, reject unauthorized verification, and append deterministic request IDs based on existing record IDs.

- [ ] **Step 4: Register the tools in `ALL_TOOLS`**

Import the functions and include them in the existing list without changing the meta-tool contract.

- [ ] **Step 5: Run banking tests and tool schema checks**

Run: `cd third_party/automationbench && pytest tests/test_benchmark_tools.py -q && pytest tests/test_tool_schemas.py -q`

Expected: PASS.

### Task 3: Add the bounded workspace/artifact state

**Files:**
- Create: `third_party/automationbench/automationbench/schema/agentic_workspace.py`
- Modify: `third_party/automationbench/automationbench/schema/world.py`
- Test: `third_party/automationbench/tests/test_benchmark_tools.py`

- [ ] **Step 1: Write the failing state test**

```python
def test_world_accepts_agentic_workspace_state():
    world = WorldState(
        agentic_workspace={
            "files": [{"path": "input.csv", "content": "name,value\nA,1\n"}],
            "artifacts": [],
        }
    )
    assert world.agentic_workspace.files[0]["path"] == "input.csv"
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `cd third_party/automationbench && pytest tests/test_benchmark_tools.py::test_world_accepts_agentic_workspace_state -q`

Expected: FAIL because the state field does not exist.

- [ ] **Step 3: Implement bounded workspace state**

Add `WorkspaceFile`, `WorkspaceArtifact`, and `AgenticWorkspaceState` models. Store file content in memory, reject absolute paths and `..` traversal, record generated artifacts separately, and keep a bounded action log.

- [ ] **Step 4: Add the state to `WorldState` and rerun tests**

Run: `cd third_party/automationbench && pytest tests/test_benchmark_tools.py::test_world_accepts_agentic_workspace_state -q`

Expected: PASS.

### Task 4: Add GDPval-inspired workspace tools

**Files:**
- Create: `third_party/automationbench/automationbench/tools/zapier/agentic_workspace.py`
- Modify: `third_party/automationbench/automationbench/tools/__init__.py`
- Test: `third_party/automationbench/tests/test_benchmark_tools.py`

- [ ] **Step 1: Write failing tests for the workspace lifecycle**

Cover:

```python
def test_workspace_can_list_read_and_write_files():
    world = make_workspace_world()
    listing = json.loads(agentic_workspace_list_files(world))
    assert listing["files"][0]["path"] == "input.csv"
    assert json.loads(agentic_workspace_read_file(world, path="input.csv"))["content"].startswith("name")
    written = json.loads(agentic_workspace_write_file(world, path="summary.md", content="# Summary"))
    assert written["created"] is True

def test_workspace_rejects_path_escape_and_records_artifact_metadata():
    world = make_workspace_world()
    error = json.loads(agentic_workspace_read_file(world, path="../secret.txt"))
    assert error["error"] == "invalid_path"
    report = json.loads(agentic_workspace_inspect_artifacts(world))
    assert report["artifacts"] == []
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `cd third_party/automationbench && pytest tests/test_benchmark_tools.py -q`

Expected: FAIL with missing workspace tool imports.

- [ ] **Step 3: Implement the minimal local tool lifecycle**

Implement:

- `agentic_workspace_list_files`
- `agentic_workspace_read_file`
- `agentic_workspace_write_file`
- `agentic_workspace_record_artifact`
- `agentic_workspace_inspect_artifacts`
- `agentic_workspace_finalize`

The tools should be deterministic and local. They should not access the real filesystem, install packages, or call the network. `record_artifact` should store path, kind, size, and optional checks; `finalize` should return the selected deliverables and mark the workspace finalized.

- [ ] **Step 4: Register the tools and run schema validation**

Run: `cd third_party/automationbench && pytest tests/test_benchmark_tools.py tests/test_tool_schemas.py -q`

Expected: PASS.

### Task 5: Add representative benchmark smoke tasks and docs

**Files:**
- Create: `third_party/automationbench/automationbench/domains/benchmark/tasks.py`
- Modify: `third_party/automationbench/automationbench/domains/__init__.py` if task discovery requires it
- Create: `third_party/automationbench/tests/test_benchmark_tasks.py`
- Modify: `benchmark/question_bank/agent/api_compatibility.md`

- [ ] **Step 1: Write failing task-structure tests**

Assert that the new banking and workspace tasks contain `initial_state`, `assertions`, and a non-empty `zapier_tools` list containing only registered tools.

- [ ] **Step 2: Run the tests and verify task getters are missing**

Run: `cd third_party/automationbench && pytest tests/test_benchmark_tasks.py -q`

Expected: FAIL because the benchmark task module does not exist.

- [ ] **Step 3: Implement two small tasks**

Add:

- `benchmark.banking_transfer_and_limit_review`, which uses both read tools and request tools and scores submitted versus completed state correctly.
- `benchmark.workspace_artifact_delivery`, which reads a seeded CSV, writes a summary artifact, records it, and finalizes only the generated deliverable.

Use partial-credit assertions that award independent points for discovery, validation, state change, artifact creation, and safe finalization.

- [ ] **Step 4: Update the compatibility note**

Document that these benchmark-inspired tools now run through the same API/tool loop, while external OpenRouter network access remains intentionally replaced by a deterministic fixture service.

- [ ] **Step 5: Run focused and full tests**

Run: `cd third_party/automationbench && pytest tests/test_benchmark_tools.py tests/test_benchmark_tasks.py tests/test_domains.py -q`

Expected: PASS.

### Task 6: Final verification and closeout

**Files:**
- Modify: `benchmark/question_bank/agent/api_compatibility.md`
- Modify: `benchmark/question_bank/agent/tasks.md` only if task tool names or score wording needs updating

- [ ] **Step 1: Run the complete AutomationBench test suite**

Run: `cd third_party/automationbench && pytest -q`

Expected: all existing tests and the new tests pass.

- [ ] **Step 2: Run the benchmark smoke tasks through the CLI**

Run the existing evaluator with the new tasks in both direct-tool and API-compatible modes, and verify that tool calls, state transitions, partial credit, and final artifacts are saved.

- [ ] **Step 3: Review the diff for unrelated changes**

Run: `git -C third_party/automationbench diff --stat` and `git -C third_party/automationbench status --short`.

Do not revert or overwrite the pre-existing modified files `automationbench/clients.py`, `tests/test_clients.py`, or the user-created helper scripts.

- [ ] **Step 4: Run Knowledge OS closeout**

Use the Knowledge OS closeout skill, update the existing canonical project note if one exists, record unresolved canonical/evidence questions in `00-入口/待处理.md`, and run `knowledge_os_lint.py`.
