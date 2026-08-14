# Model Evaluation Repository Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate the scattered model-evaluation assets into one local canonical project that can be reproduced from a README and later pushed to a private GitHub repository.

**Architecture:** Preserve source directories and build a curated canonical tree under `<canonical-project-root>`. Separate reusable source, benchmark data, runners, evaluation, examples, and operational documentation. Keep provider credentials outside Git and use manifests plus pinned dependencies rather than copying local environments.

**Tech Stack:** Python projects with `pyproject.toml`, existing model API collector, existing AutomationBench integration, YAML/JSON benchmark manifests, shell bootstrap scripts, Git, GitHub CLI if authenticated, and a Codex Skill under `skills/model-evaluation-repro`.

---

### Task 1: Inventory Source Inputs

**Files:**
- Create: `inventory/source-manifest.json`
- Create: `inventory/README.md`

- [ ] **Step 1: Record candidate source directories**

Run:

```bash
find <source-root>/模型测评 \
  <source-root>/模型测评题库 \
  <source-root>/模型测试大师 \
  <source-root>/模型测评_new \
  -maxdepth 2 -type f \
  -not -path '*/.git/*' \
  -not -path '*/.venv/*' \
  -not -path '*/node_modules/*' \
  -not -path '*/.playwright-cli/*' \
  -print | sort
```

- [ ] **Step 2: Classify files**

Classify each candidate as `include`, `review`, `example-only`, or `exclude`.
Include source code, benchmark definitions, schemas, tests, and method docs.
Exclude caches, virtual environments, browser state, generated logs, and
unreviewed credentials. Mark historical outputs and large media as
`example-only` or `review`.

- [ ] **Step 3: Save the manifest**

Write `inventory/source-manifest.json` with source path, destination path,
classification, reason, and size. Write `inventory/README.md` explaining that
the manifest is the provenance record for consolidation.

- [ ] **Step 4: Verify the inventory**

Run:

```bash
python3 -m json.tool inventory/source-manifest.json >/dev/null
```

Expected: exit code `0`.

### Task 2: Build the Canonical Tree

**Files:**
- Create: `benchmark/`, `runners/`, `evaluation/`, `configs/`, `scripts/`, `examples/`, `tests/`, `docs/`
- Copy: approved files from the inventory into the canonical tree

- [ ] **Step 1: Create destination directories**

Run:

```bash
mkdir -p benchmark/{agent,multimodal,reasoning,manifests,schemas} \
  runners/{model-api-collector,agent-runner} \
  evaluation/{graders,schemas,reports} \
  configs scripts examples/{inputs,results} tests docs inventory skills
```

- [ ] **Step 2: Copy only approved source**

Use `rsync` with explicit excludes for `.venv`, `node_modules`, caches,
Playwright artifacts, secrets, and generated run directories. Do not delete
anything from the source directories.

- [ ] **Step 3: Normalize project-local paths**

Search copied files for machine-specific absolute paths and replace them with
repository-relative paths or documented environment variables. Keep the
original files unchanged.

- [ ] **Step 4: Verify the copied tree**

Run:

```bash
rg -n 'BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|sk-[A-Za-z0-9]' .
```

Expected: no credentials and no unreviewed machine-specific paths.

### Task 3: Add Reproduction Configuration

**Files:**
- Create: `.env.example`
- Create: `configs/providers.example.yaml`
- Create: `configs/models.example.yaml`
- Create: `pyproject.toml`
- Create: `scripts/bootstrap.sh`

- [ ] **Step 1: Define provider-neutral configuration**

Include provider, base URL, model ID, protocol, API-key environment variable,
timeout, retry, concurrency, and safety-stop fields. Never include a real key.

- [ ] **Step 2: Define the install entry point**

Make `scripts/bootstrap.sh` create a local Python environment, install the
root project and pinned subprojects, and print the next README command without
printing secret values.

- [ ] **Step 3: Add configuration validation**

Add a small validator that checks required names and supported protocols while
allowing the API key value to remain in the environment.

- [ ] **Step 4: Add tests**

Test valid config, missing key variable, unsupported protocol, and model
selection. Run the focused test file and expect all tests to pass.

### Task 4: Write the Reproduction README

**Files:**
- Create: `README.md`
- Create: `docs/methodology.md`
- Create: `docs/architecture.md`
- Create: `docs/reproduction.md`
- Create: `docs/model-integration.md`
- Create: `docs/scoring.md`

- [ ] **Step 1: Explain the evaluation contract**

Document the distinction between single-request evaluation and full Agent
evaluation, including tools, state transitions, multi-turn loops, assertions,
and scoring.

- [ ] **Step 2: Document clean-clone setup**

Include exact commands for clone, bootstrap, local validation, provider
configuration, smoke test, selected benchmark run, and result inspection.

- [ ] **Step 3: Document model integration**

Explain how to add an OpenAI-compatible provider such as
`lingzhi.agibot.com/v1` without embedding credentials, and how to verify the
model ID before a full run.

- [ ] **Step 4: Document reproducibility limits**

State which artifacts are pinned and which upstream conditions can drift:
model behavior, provider availability, rate limits, pricing, and external
service data.

### Task 5: Add Verification and Example Artifacts

**Files:**
- Create: `scripts/smoke-test.sh`
- Create: `scripts/run-evaluation.sh`
- Create: `examples/results/sample-run.json`
- Create: `tests/test_repository_layout.py`
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Add no-network smoke test**

Run the config validator, dataset validator, and fake-provider path without
external API calls.

- [ ] **Step 2: Add optional live smoke test**

Require an explicit environment variable and one selected model. Refuse to
run when the key is missing, and limit the request count to one.

- [ ] **Step 3: Define the result schema**

Store provider, model, benchmark version, task ID, request metadata, response
metadata, score, assertion results, errors, and timestamps.

- [ ] **Step 4: Add CI**

Run layout, config, dataset, and unit tests in GitHub Actions without any
external API key.

### Task 6: Create the Codex Skill

**Files:**
- Create: `skills/model-evaluation-repro/SKILL.md`
- Create: `skills/model-evaluation-repro/references/provider-config.md`
- Create: `skills/model-evaluation-repro/references/reproduction-workflow.md`
- Create: `skills/model-evaluation-repro/scripts/validate_project.py`

- [ ] **Step 1: Define triggers and safety boundaries**

Trigger on requests to configure a model, validate an API, run the benchmark,
or interpret a result. Require explicit provider/model selection before live
calls and never expose secret values.

- [ ] **Step 2: Encode the workflow**

Guide discovery, config validation, no-network checks, optional one-request
smoke test, benchmark execution, result archival, and failure diagnosis.

- [ ] **Step 3: Validate the Skill**

Run the Skill validator and test it against the local canonical tree.

### Task 7: Initialize and Review Git

**Files:**
- Create: `.gitignore`
- Create: `LICENSE`
- Create: `THIRD_PARTY_NOTICES.md`

- [ ] **Step 1: Add ignore rules**

Ignore `.env`, `.venv`, `node_modules`, caches, browser artifacts, raw logs,
temporary files, and generated results except for explicitly curated examples.

- [ ] **Step 2: Run secret and size checks**

Check tracked candidates for credential patterns and files larger than the
repository threshold. Review every `review` item from the inventory.

- [ ] **Step 3: Initialize the local repository**

Run `git init`, add only the reviewed canonical tree, and create an initial
local commit after verification.

### Task 8: Create the Private GitHub Repository

**Files:**
- Modify: `README.md` with the final repository URL after creation

- [ ] **Step 1: Confirm GitHub destination**

Resolve the GitHub owner and repository name; do not guess an organization or
overwrite an existing repository.

- [ ] **Step 2: Create a private repository**

Use the authenticated GitHub CLI or the GitHub web UI to create a new private
repository with no accidental public visibility.

- [ ] **Step 3: Push and verify**

Push the reviewed local commit, confirm repository visibility, inspect the
remote file tree, and clone into a temporary directory to run the clean-clone
validation.
