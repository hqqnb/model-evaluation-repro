# 结果归档

这里说明测评结果如何保存和复核。它不存放默认运行产生的大量结果文件；
正式运行结果应按运行批次和题库版本单独归档，并遵守仓库的脱敏和保密边界。

每个结果至少应能对应到：

- 题库版本和题目编号；
- 服务商、模型 ID、接口类型和实际请求参数；
- 原始回答或交付物；
- Coding 的运行或黑盒测试结果；
- Agent 的工具轨迹、最终状态和逐项断言；
- 评分明细、错误信息、重试情况和人工复核结论。

`examples/results/sample-run.json` 只展示结果结构，不代表真实测评成绩。
不要把 API Key、Cookie、本地登录态、未脱敏业务数据或大批量临时运行日志写入仓库。

当前 Agent 结果归档位于 [`evaluation/agent/`](agent/)，其中正式总分、最终批次摘要、交互证据和人工复核材料分开保存。

当前单轮补跑批次位于 [`evaluation/single_turn/recovery-20260817/`](single_turn/recovery-20260817/)，包含 7 个此前缺失或技术失败单元的状态记录；成功回答追加在 [`benchmark/question_bank/single_turn/outputs/results.jsonl`](../benchmark/question_bank/single_turn/outputs/results.jsonl)。
