# 模型输出记录

`results.jsonl` 用于保存模型的原始输出，每行一个 JSON 对象：

```json
{"run_id":"...","model":"...","item_id":"...","output":"...","created_at":"..."}
```

不要把答案或人工评分写入原始输出文件；评分结果可以在后续单独添加到受限目录。

2026-08-17 的补跑结果见 [`evaluation/single_turn/recovery-20260817/`](../../../../evaluation/single_turn/recovery-20260817/)；
其中 `results.jsonl` 只追加接口成功返回的原始回答，失败请求的状态和错误信息见该批次的
`summary.json`。
