# Model Evaluation Reproducible Repository Design

## Goal

Create one canonical local project and private GitHub repository that lets another
researcher understand the evaluation methodology from `README.md`, configure
their own model API credentials, run a smoke test, and reproduce selected
benchmark runs without relying on this Mac's directory layout or login state.

## Scope

The canonical repository will consolidate the reusable parts of:

- the model API collector and its tests;
- the model evaluation question bank and dataset validation/export tools;
- the Agent benchmark question bank and the AutomationBench-based execution path;
- scoring, result schemas, sample outputs, and evaluation documentation;
- provider/model configuration examples and local bootstrap/run scripts;
- a Codex Skill that guides API validation, benchmark execution, scoring, and
  result interpretation.

The repository will not include real API keys, browser sessions, local virtual
environments, `node_modules`, caches, raw browser logs, or unreviewed private
business data. Original source directories will remain untouched until the
canonical copy has been checked.

## Reproduction Contract

The first release must support:

1. cloning the private repository;
2. installing the documented Python and JavaScript dependencies;
3. copying `.env.example` to a local environment file and setting a user's own
   API key;
4. running a no-cost local validation and a one-model smoke test;
5. running a selected benchmark manifest;
6. producing a standard result artifact with model, provider, benchmark version,
   timestamps, request/response metadata, score, and error information.

Exact historical score reproduction is best-effort because upstream model
behavior, pricing, rate limits, and hosted API responses may change. The
repository will preserve the question-bank snapshot and run manifest required
to explain historical results.

## Proposed Repository Layout

```text
model-evaluation/
├── README.md
├── LICENSE
├── THIRD_PARTY_NOTICES.md
├── .env.example
├── .gitignore
├── pyproject.toml
├── docs/
│   ├── methodology.md
│   ├── architecture.md
│   ├── reproduction.md
│   ├── model-integration.md
│   └── scoring.md
├── benchmark/
│   ├── agent/
│   ├── multimodal/
│   ├── reasoning/
│   ├── manifests/
│   └── schemas/
├── runners/
│   ├── model-api-collector/
│   └── agent-runner/
├── evaluation/
│   ├── graders/
│   ├── schemas/
│   └── reports/
├── configs/
│   ├── models.example.yaml
│   └── providers.example.yaml
├── scripts/
│   ├── bootstrap.sh
│   ├── smoke-test.sh
│   └── run-evaluation.sh
├── examples/
│   ├── inputs/
│   └── results/
├── tests/
└── skills/
    └── model-evaluation-repro/
```

Third-party benchmark engines will be pinned to a commit or release and
documented in `THIRD_PARTY_NOTICES.md`. They will only be vendored when the
license and size make that the safest reproducibility choice.

## Provider Configuration

Model adapters will use a provider-neutral configuration with:

- provider name;
- OpenAI-compatible base URL;
- model ID;
- protocol (`chat_completions`, `responses`, or other supported adapter);
- API-key environment variable name;
- optional timeout, retry, concurrency, and safety-stop settings.

For example, `qwen3.8-max` will be represented by configuration only. The
repository will not store the actual key or assume a specific personal account.

## Validation

Before the first GitHub push, the canonical project will pass:

- dataset and manifest validation;
- unit tests for provider configuration and result schemas;
- a local no-network smoke test using a fake provider;
- a live one-request smoke test only when the user supplies an API key and
  explicitly selects a provider/model;
- a clean-clone reproduction check using the README commands.

## Operational Safety

- Existing source directories are copied, not deleted.
- GitHub repository creation and first push happen only after a secret scan and
  a user-visible file manifest review.
- The Skill must never print or commit secret values.
- Potentially sensitive or ambiguous files are marked for review rather than
  silently included or deleted.
