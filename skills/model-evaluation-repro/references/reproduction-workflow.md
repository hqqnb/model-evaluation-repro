# Reproduction Workflow Reference

## Local-only phase

Run `./scripts/smoke-test.sh`. This checks repository configuration, benchmark
question counts, answer/rubric alignment, and local asset references without
calling a model.

## One-request phase

Use `scripts/run-evaluation.sh` with one model and the harmless example prompt.
Confirm:

- the provider is reachable;
- authentication succeeds;
- the model ID is accepted;
- the protocol matches the endpoint;
- the result archive contains request metadata and a final answer;
- the account's cost or free-quota protection is appropriate.

## Batch phase

Before a batch run, pin:

- repository commit;
- question-bank manifest;
- model ID and provider;
- protocol and reasoning settings;
- repeat count;
- concurrency and maximum Agent steps;
- result export path.

Start with one task and `max-concurrent=1`. Increase scope only after the
small run is correct.

## Agent phase

An Agent run is valid only when the runner executes model tool calls, mutates a
simulated environment, returns tool results for subsequent turns, and scores
the final state. Preserve the trajectory and assertion details.
