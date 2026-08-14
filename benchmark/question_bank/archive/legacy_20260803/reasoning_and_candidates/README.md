# 推理能力候选题库

本目录包含第一版 20 道推理能力候选题及其确定性判分工具。

正式题库与简明说明：

- `FORMAL_QUESTION_BANK.md`：21 道正式题的统一题面、环境、评分和实施边界。
- `MODEL_BENCHMARK_OVERVIEW.md`：省略实现细节的题库说明和结果解读方式。

Agent 题库另见：

- `AGENT_TASKS.md`：6 道面向旗舰模型的 Agent 正式候选题，包含模型题面、模拟环境、隐藏异常、目标终态和机器评分要求。
- `../docs/superpowers/plans/2026-08-03-human-auditable-agent-pilot.md`：A01 旅行中断题的模拟环境实现计划。

Coding 题库另见：

- `CODING_TASKS.md`：6 道面向旗舰模型的 Coding 正式候选题，包含初始代码库、隐藏测试方向、评分项和人类证据卡。

## 文件

- `QUESTIONS.md`：可直接审阅的完整题面，不含答案。
- `questions.json`：供自动测试系统读取的题目、难度、分类和评分元数据。
- `answer_key.json`：隐藏答案、近似错误答案、简要解法和验证方式，不得提供给被测模型。
- `grade.py`：解析结构化模型输出并确定性判分。
- `reference_checks.py`：独立重算 20 道题答案，对有限问题执行枚举、搜索或动态规划。
- `validate_bank.py`：检查题目数量、总分、难度分布、分类覆盖和答案一致性。

## 检查

```bash
python3 -m unittest discover -s tests -v
python3 -m benchmark.validate_bank
```

## 当前边界

当前版本已经完成题面完整性、答案一致性、唯一答案和判分规则检查，可以进入多模型预跑。

题目的实际区分度不能仅由设计推断。预跑后应依据通过率、强弱模型通过差、重复测试波动和失败原因继续筛题或调整难度。

## 短题型高难逻辑题

- `SHORT_HARD_LOGIC_TASKS.md`：6 道完整公开题面，不含答案。
- `short_logic_answer_key.json`：私有答案、近似错误答案和字段分值。
- `short_logic/`：可能世界、最小修复、稳健计划、自指陈述、隐藏信息策略和因果干预的确定性求解器及测试。
- API 输入：`runners/model-api-collector/prompts/reasoning_short_hard_20260806.jsonl`。

该组题先通过静态验证，再选择 3 个强模型小规模预跑。至少 4 道题出现语义差异后，才扩展到全部 7 个模型。
