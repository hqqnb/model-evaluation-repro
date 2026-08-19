# 模型测评项目

这是一个把**题库设计、模型调用、Agent 工具执行、评分复核和结果归档**放在同一个仓库里的大模型测评项目。仓库的重点不是只给模型排一个名次，而是记录：

- 测评题目为什么这样设计；
- 不同题型应该使用哪条评测链路；
- Agent 是否真的完成了工具调用、状态变化和交付；
- 结果如何评分、复核和解释；
- 后续同事如何定位题目、代码、结果和证据。

## 当前归档快照

本仓库是对截至 **2026-08-17** 已完成工作的单仓归档。当前有效的主要成果包括：

| 模块 | 当前内容 | 入口 |
| --- | --- | --- |
| 项目总览 | 工作范围、方法、版本和结论 | [`docs/工作总览.md`](docs/工作总览.md) |
| 统一题库 | 推理、Coding、多模态和 Agent 四类题目，共 28 道 | [`benchmark/question_bank/manifest.json`](benchmark/question_bank/manifest.json) |
| Agent 题库 | T01-T08、评分规则和 API 兼容性说明 | [`benchmark/question_bank/agent/`](benchmark/question_bank/agent/) |
| API 采集 | 单轮回答采集器、Provider 配置和测试 | [`runners/model-api-collector/`](runners/model-api-collector/) |
| Agent 执行 | 定制版 AutomationBench、工具、状态、断言和运行脚本 | [`third_party/automationbench/`](third_party/automationbench/) |
| 正式总分 | 人工确认后的 Agent 汇总分数 | [`evaluation/agent/formal_scores_20260815.json`](evaluation/agent/formal_scores_20260815.json) |
| 最终批次摘要 | `agent-suite-v1.1-tool-errors-noleak-20260815` 的运行摘要 | [`evaluation/agent/formal_suite_summary_20260815.md`](evaluation/agent/formal_suite_summary_20260815.md) |
| 交互证据 | 8 道题、10 个模型、80 份已脱敏回答记录 | [`evaluation/agent/evidence/20260814-agent/`](evaluation/agent/evidence/20260814-agent/) |
| 结果发布工具 | 评分整理、脱敏、复核和知识库链接回填脚本 | [`tools/`](tools/) |
| 单轮补跑批次 | 2026-08-17 缺口补跑、流式修复和 C08 继续运行记录 | [`evaluation/single_turn/stream-fix-20260817/`](evaluation/single_turn/stream-fix-20260817/) |
| 可复用测评 Skill | 新模型接入、运行、恢复、评分、GitHub 预览和如流回填全链路 | [`skills/model-evaluation-repro/SKILL.md`](skills/model-evaluation-repro/SKILL.md) |

## 先看什么

如果你只是想快速理解项目，按下面顺序阅读：

1. [`docs/工作总览.md`](docs/工作总览.md)：看完整工作分解、每部分做了什么、目前处于什么状态。
2. [`benchmark/question_bank/manifest.json`](benchmark/question_bank/manifest.json)：看统一题库的版本和题型范围。
3. [`benchmark/question_bank/agent/tasks.md`](benchmark/question_bank/agent/tasks.md)：看 Agent 八道正式题目和评分口径。
4. [`evaluation/agent/formal_scores_20260815.json`](evaluation/agent/formal_scores_20260815.json)：看项目采用的正式总分。
5. [`evaluation/agent/formal_suite_summary_20260815.md`](evaluation/agent/formal_suite_summary_20260815.md)：看最终 Agent 批次的技术状态、平均分和严格通过率。
6. [`docs/reproduction.md`](docs/reproduction.md)：看如何在不暴露密钥的情况下进行本地验证或重新运行。

本轮补跑与修复共形成 7 个可追溯结果：Opus 4.8 的 2 道推理题复用
2026-08-15 的最高强度流式成功运行，Opus 5 的 5 道 Coding 题均已取得
完整接口回答，其中 C08 的回答仍需检查是否真正交付了项目产物。失败原因、
重试策略和请求元数据见 [`evaluation/single_turn/stream-fix-20260817/`](evaluation/single_turn/stream-fix-20260817/)；
不自动改写正式分数。

## 测评链路

仓库中保留两条不同的评测链路，不能混用：

### 单轮 API 采集

适用于推理、Coding 和部分多模态题目。采集器负责发送一次请求并保存原始回答、推理内容、Token、耗时和错误。

入口：

- [`runners/model-api-collector/README.md`](runners/model-api-collector/README.md)
- [`scripts/run-evaluation.sh`](scripts/run-evaluation.sh)
- [`benchmark/question_bank/single_turn/`](benchmark/question_bank/single_turn/)

这条链路**不执行工具调用，也不维护外部环境状态**，因此不能把单次工具调用文本当成完整 Agent 测评。

### 多轮 Agent 执行

适用于 T01-T08 Agent 题目。运行器会加载初始状态，向模型提供工具，执行模型发起的工具调用，把结果回传给模型，并根据最终环境状态和断言评分。

入口：

- [`third_party/automationbench/README.md`](third_party/automationbench/README.md)
- [`third_party/automationbench/automationbench/scripts/formal_agent_suite.py`](third_party/automationbench/automationbench/scripts/formal_agent_suite.py)
- [`benchmark/question_bank/agent/api_compatibility.md`](benchmark/question_bank/agent/api_compatibility.md)

这条链路评价的是“模型 + 工具 + 环境状态 + 断言”的完整闭环，而不是模型对工具调用的文字描述。

## 正式结果的阅读边界

仓库中有两类结果，含义不同：

- [`formal_scores_20260815.json`](evaluation/agent/formal_scores_20260815.json)：人工确认后登记的项目正式总分，当前排名和对外汇总以其中的 `official_score` 为准。
- [`formal_suite_summary_20260815.json`](evaluation/agent/formal_suite_summary_20260815.json)：某一个最终批次的运行摘要，记录该批次的平均加权分、严格通过率、技术失败和预检状态。

两者不能直接混成一个排名。正式总分包含人工汇总口径；批次摘要用于说明某一轮实际运行的结果和技术完整性。

## 复现与安全

默认先运行不访问外部 API 的检查：

```bash
./scripts/bootstrap.sh
./scripts/smoke-test.sh
python3 scripts/validate_project.py
python3 benchmark/question_bank/validate_manifest.py
```

正式运行前需要明确记录题库版本、模型 ID、服务商、接口协议、并发、最大步数和输出目录。不要把 API Key、Cookie、本地登录态、`.env` 文件或未脱敏业务数据写入仓库。

仓库中的 Agent 交互记录已经做过密钥脱敏；大量临时运行目录、浏览器缓存、虚拟环境、失败探针和本地备份没有纳入公开归档。

## 目录结构

```text
benchmark/
  question_bank/              统一题库、评分规则和历史候选题
configs/                      不含密钥的 Provider/Model 配置示例
docs/                         方法、架构、复现、工作总览和实施计划
evaluation/                   结果说明、正式分数和脱敏证据
runners/                     单轮 API 采集器
scripts/                     项目级验证和运行入口
tests/                       项目级测试
third_party/automationbench/  定制后的 Agent 执行和评分环境
tools/                       结果复核、脱敏和发布工具
```

## 版本和归档原则

- 当前有效代码每个模块只保留一份，不在目录中复制多个历史版本。
- 版本变化优先通过 Git 提交记录查看；只有对复盘有价值的材料才进入归档或证据目录。
- 运行结果按题库版本、批次和模型区分；不能把失败重跑或 smoke 结果当成正式结果。
- 如果未来更新题库、评分口径或正式总分，应同步更新对应 manifest、工作总览和结果说明。

## 许可证与第三方代码

第三方 AutomationBench 的许可证和来源说明见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) 及 [`third_party/automationbench/LICENSE`](third_party/automationbench/LICENSE)。
