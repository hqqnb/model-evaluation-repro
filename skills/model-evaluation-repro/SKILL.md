---
name: model-evaluation-repro
description: Use when configuring a model provider, validating an evaluation repository, running a model or Agent benchmark, or explaining reproducible evaluation results.
---

# Model Evaluation Repro

Use this skill for the canonical model-evaluation repository or a clean clone
with the same layout.
The goal is to make evaluation runs understandable, bounded, and repeatable.

## Safety Rules

- Never print, copy, commit, or include an API key, cookie, browser session, or
  local `.env` file.
- A live API call requires an explicit provider and model from the user.
- Start with the no-network checks. For a new provider, prefer one request with
  one harmless prompt before any batch run.
- Do not claim exact score reproduction when an upstream model, service, or
  dataset can drift. Record the manifest, parameters, and upstream identifiers.
- Treat internal answer keys and rubrics as private evaluation material; never
  send them to the model.

## Workflow

1. Identify the requested operation: local validation, provider setup, one-call
   smoke test, single-task run, batch run, Agent run, or result interpretation.
2. Read the repository `README.md` and the relevant reference:
   - provider or model setup: `references/provider-config.md`;
   - reproduction or run request: `references/reproduction-workflow.md`.
3. Run:

   ```bash
   ./scripts/smoke-test.sh
   ```

4. For a live request, check only whether the configured key environment
   variable is present. Do not reveal its value. Confirm the model ID and
   endpoint before invoking the API.
5. Use `scripts/run-evaluation.sh` for the one-request collector smoke test.
   Use the AutomationBench CLI only when the user requested an Agent run and
   the third-party environment is installed.
6. Save or inspect the standard result artifact. Report provider, model,
   benchmark version, request count, score, errors, and any reproducibility
   limits.

## Choosing the Runner

- Use `runners/model-api-collector` for one-shot answers, reasoning, coding,
  and multimodal response collection.
- Use `benchmark/question_bank/agent` and `third_party/automationbench` for
  multi-turn tool execution with simulated state and assertions.
- Use `benchmark/question_bank/single_turn/source_material/评测脚本`
  for the deterministic Coding graders.
- Do not turn an Agent task into a plain text prompt and call the result a
  full Agent evaluation.

## Useful Commands

```bash
./scripts/bootstrap.sh
./scripts/smoke-test.sh
ENV_FILE=.env.local CONFIG=runners/model-api-collector/config/qwen.yaml \
  ./scripts/run-evaluation.sh qwen3.8-max
```

For a full run, first select a manifest and set `--repeat`, concurrency, step
limits, and export paths explicitly. Start with one task and one concurrent
request, then scale only after checking the result and cost boundary.

## Result Interpretation

Always distinguish:

- `partial_credit` from strict completion;
- model text from tool trajectory;
- requested parameters from effective upstream parameters;
- local public-task scores from official held-out benchmark scores;
- an API failure from a model capability failure.

If a run fails, preserve the request metadata and error response, then diagnose
provider reachability, authentication, model ID, protocol, rate limits, and
task/tool compatibility in that order.
