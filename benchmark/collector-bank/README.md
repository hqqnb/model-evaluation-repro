# 大模型评测题库（私有）

本仓库保存从内部知识库整理的模型评测题目，供后续自动化评测和结果沉淀使用。仓库应保持 **Private**，不要把 `rubrics/`、`assets/` 或模型输出公开到公共仓库。

## 目录

- `dataset/prompts.json`：可直接下发给模型的题目，不包含标准答案。
- `rubrics/rubrics.json`：内部答案、能力标签和人工评审标准，不得下发给模型。
- `assets/`：多模态题目所需图片。
- `outputs/results.jsonl`：模型原始输出记录，每行一条结果。
- `scripts/validate_dataset.py`：检查题目、评分和图片引用完整性。
- `scripts/record_output.py`：追加模型输出记录。

## 评测流程

1. 评测程序只读取 `dataset/prompts.json`。
2. 每次请求只发送一个题目和其 `attachments`。
3. 将模型原始输出通过 `scripts/record_output.py` 写入 `outputs/results.jsonl`。
4. 评审人员使用 `rubrics/rubrics.json` 进行人工评分；Coding 题可在此基础上接入项目级自动测试。
5. 运行 `python3 scripts/validate_dataset.py` 检查数据完整性。

## 记录输出

```bash
python3 scripts/record_output.py \
  --run-id 2026-08-06-demo \
  --model model-name \
  --item-id reasoning-r01 \
  --output-file /tmp/model-output.txt
```

输出文件采用 JSONL，建议不要覆盖原始记录；每次评测使用新的 `run_id`。
