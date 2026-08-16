# 复现指南

## Clean clone

```bash
git clone https://github.com/hqqnb/model-evaluation-repro.git
cd model-evaluation-repro
./scripts/bootstrap.sh
cp .env.example .env.local
./scripts/smoke-test.sh
```

正式题库由 [`benchmark/question_bank/manifest.json`](../benchmark/question_bank/manifest.json)
统一管理。开始运行前先确认题库版本、题量和题型范围，不要从历史归档目录直接挑题。

## API smoke test

先在服务商控制台确认模型 ID、免费额度保护和调用协议，再设置对应环境变量：

```bash
export LINGZHI_API_KEY='your-local-key'
ENV_FILE=.env.local \
CONFIG=runners/model-api-collector/config/qwen.yaml \
./scripts/run-evaluation.sh qwen3.8-max
```

第一次只运行一题一次。确认结果文件和费用状态后，再根据统一题库清单选择正式运行范围。

## Agent evaluation

AutomationBench 依赖 Python 3.13。安装后，按其 README 运行指定任务，并同时记录：

- `--model`；
- `--base-url`；
- `--api-key-var`；
- `--api` 或 `--responses-api`；
- `--toolset`；
- `--max-steps`；
- `--max-concurrent`；
- 题库版本和导出文件路径。

正式测评默认使用 `--max-concurrent 1` 先验证单题，再逐步增加并发，避免错误配置放大费用。

本仓库当前归档的 Agent 题库版本是
`agent-suite-v1.0-20260814`，最终批次摘要位于
[`evaluation/agent/formal_suite_summary_20260815.md`](../evaluation/agent/formal_suite_summary_20260815.md)。
如果只是复核已有结果，优先阅读该摘要和
[`evaluation/agent/formal_scores_20260815.json`](../evaluation/agent/formal_scores_20260815.json)，不要从历史运行目录重新拼接正式总分。
