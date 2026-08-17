# 如流主表缺口补跑：2026-08-17

本批次以如流主文档《大模型评测@20260817》的主表为缺口来源，
针对 10 个“未完成/未交付/API 限流”单元进行单次补跑。

## 结果

| 模型 | 题目 | 状态 | 说明 |
| --- | --- | --- | --- |
| Opus 4.8 | `reasoning-r01` | failed | HTTP 504 |
| Opus 4.8 | `reasoning-r03` | failed | HTTP 504 |
| Opus 5 | `multimodal-mm04` | success | 接口成功，待人工评分 |
| Opus 5 | `coding-c01` | failed | HTTP 500 |
| GPT 5.5 | `coding-c06` | success | 接口成功，待 Coding 交付物检查 |
| Opus 4.8 | `coding-c06` | success | 接口成功，待 Coding 交付物检查 |
| Opus 5 | `coding-c05` | failed | HTTP 500 |
| Opus 5 | `coding-c06` | failed | HTTP 500 |
| Opus 5 | `coding-c07` | failed | HTTP 504 |
| Opus 5 | `coding-c08` | failed | HTTP 500 |

机器可读状态见 [`summary.json`](summary.json)，3 份接口成功回答见
[`successful_outputs.jsonl`](successful_outputs.jsonl)。

## 执行参数

- 每个单元只发送 1 次逻辑请求。
- Opus 4.8、Opus 5 使用 `reasoning_effort: max`。
- GPT 5.5 使用 `reasoning_effort: xhigh`。
- 统一使用完整响应模式，未把本批次结果自动覆盖到如流主表。

本批次的成功状态不等于评分通过；多模态题和 Coding 题需要先完成内容/交付物复核，再决定是否回填分数和预览链接。
