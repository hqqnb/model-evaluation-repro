# 单轮补跑批次：2026-08-17

本批次针对此前没有成功结果的 7 个单元进行单次补跑，使用统一题库
`model-evaluation-20260815`，完整响应模式，未发送内部答案或评分细则。

## 结果

| 模型 | 题目 | 状态 | 说明 |
| --- | --- | --- | --- |
| DeepSeek V4 Pro | `coding-c08` | success | 已保存原始回答 |
| Opus 5 | `multimodal-mm01` | success | 接口成功，但模型无法完成图像识别 |
| Opus 5 | `multimodal-mm04` | success | 已保存原始回答 |
| GLM-5.2 | `reasoning-r01` | failed | HTTP 200，空响应 |
| Opus 5 | `coding-c01` | failed | HTTP 500 |
| Opus 5 | `coding-c07` | failed | HTTP 504 |
| Opus 5 | `coding-c08` | failed | HTTP 500 |

完整的机器可读记录见 [`summary.json`](summary.json)。成功回答已追加到
[`single_turn/outputs/results.jsonl`](../../../benchmark/question_bank/single_turn/outputs/results.jsonl)。

## 运行边界

- 每个单元只执行 1 次逻辑请求。
- 本批次只记录补跑结果，不覆盖此前的失败记录，也不自动更新正式分数。
- `multimodal-mm01` 的 `success` 是接口层成功，不代表题目作答正确；需要后续按多模态评分细则人工复核。
- Coding 题的交付物和黑盒测试尚未在本批次自动评分。
