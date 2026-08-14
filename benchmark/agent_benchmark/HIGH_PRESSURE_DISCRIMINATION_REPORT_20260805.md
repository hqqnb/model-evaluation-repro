# 长任务型推理题区分度 Pilot

日期：2026-08-05

## 1. 总览

- 结果记录：70 条；
- 全员通过题：0 道；
- 通过率处于 2/7 至 5/7 的题：4 道；
- 模型分数梯队：4 个。

### 核心判断

- 语义推理错误：3 次；长程交付失败：11 次。
- 真正产生语义错误的题：T01、T02、T06。
- 只产生未完成或接口失败的题：T03、T04、T05、T07、T08、T09、T10。
- 在成功返回的请求中没有语义失分的模型：Opus 5、gpt-5.6-sol、hy3、kimi-k3、qwen3.8-max。

| 模型 | 总分 | 整题正确 | 部分正确 | 未完成 | 接口失败 | 格式不合规 |
|---|---:|---:|---:|---:|---:|---:|
| Opus 5 | 100 | 10/10 | 0 | 0 | 0 | 10 |
| hy3 | 100 | 10/10 | 0 | 0 | 0 | 0 |
| kimi-k3 | 100 | 10/10 | 0 | 0 | 0 | 0 |
| qwen3.8-max | 100 | 10/10 | 0 | 0 | 0 | 0 |
| gpt-5.6-sol | 90 | 9/10 | 0 | 0 | 1 | 0 |
| GLM-5.2 | 51 | 5/10 | 1 | 2 | 0 | 4 |
| DeepSeek-V4-Flash | 20 | 2/10 | 0 | 8 | 0 | 8 |

## 2. 逐题结果

| 题目 | 名称 | 整题通过 | 平均得分 | 状态分布 |
|---|---|---:|---:|---|
| T01 | 火车售票 | 5/7 | 7.14/10 | correct=5、unfinished=1、wrong=1 |
| T02 | 交织档案解读 | 5/7 | 7.14/10 | correct=5、unfinished=1、wrong=1 |
| T03 | 观棋不语 | 6/7 | 8.57/10 | correct=6、unfinished=1 |
| T04 | 年会抽奖审计 | 6/7 | 8.57/10 | correct=6、unfinished=1 |
| T05 | 大状态机器操作 | 5/7 | 7.14/10 | correct=5、unfinished=2 |
| T06 | 字符矩阵 | 6/7 | 8.71/10 | correct=6、partial=1 |
| T07 | 目标穷举 | 5/7 | 7.14/10 | api_failure=1、correct=5、unfinished=1 |
| T08 | 信息解压 | 6/7 | 8.57/10 | correct=6、unfinished=1 |
| T09 | 管道疏通 | 6/7 | 8.57/10 | correct=6、unfinished=1 |
| T10 | 激光布局 | 6/7 | 8.57/10 | correct=6、unfinished=1 |

## 3. 验收标准

- 通过：最多3道全员通过。
- 未通过：至少6道通过率为2/7至5/7。
- 通过：至少3个分数梯队。
- 通过：结果完整覆盖70次调用。

## 4. 题目处理建议

- 保留为核心推理诊断：T01、T02、T06。这些题至少让一个模型给出了可解析但语义错误的答案。
- 仅作为长程交付压力测试：T03、T04、T05、T07、T08、T09、T10。这些题没有制造语义差异，不能据此给完成作答的旗舰模型排序。
- 本轮可以区分中低表现模型，但旗舰模型上限已明显饱和；下一轮应提高推理结构难度，而不是继续增加输入长度或机械步骤。

## 5. 失败明细

- T01 / DeepSeek-V4-Flash：unfinished，得分 0/10，错误字段 availability、active_orders、waiting_orders、failed_operations。
- T01 / GLM-5.2：wrong，得分 0/10，错误字段 availability、active_orders、waiting_orders、failed_operations。
- T02 / DeepSeek-V4-Flash：unfinished，得分 0/10，错误字段 facts、overridden_ids、system_record_count。
- T02 / GLM-5.2：wrong，得分 0/10，错误字段 facts、overridden_ids、system_record_count。
- T03 / GLM-5.2：unfinished，得分 0/10，错误字段 STEP、CAPTURE、STAR、WIN、Q_legal_moves、R。
- T04 / DeepSeek-V4-Flash：unfinished，得分 0/10，错误字段 winners、invalid_draws、department_counts。
- T05 / DeepSeek-V4-Flash：unfinished，得分 0/10，错误字段 final_state、illegal_commands、successful_mix_count。
- T05 / GLM-5.2：unfinished，得分 0/10，错误字段 final_state、illegal_commands、successful_mix_count。
- T06 / GLM-5.2：partial，得分 1/10，错误字段 patterns_by_row、rows、checksum。
- T07 / DeepSeek-V4-Flash：unfinished，得分 0/10，错误字段 combinations、count、first、last。
- T07 / gpt-5.6-sol：api_failure，得分 0/10，错误字段 无可提取字段。
- T08 / DeepSeek-V4-Flash：unfinished，得分 0/10，错误字段 blocks、decoded、length_without_separators、count_R、checksum_mod_997。
- T09 / DeepSeek-V4-Flash：unfinished，得分 0/10，错误字段 sequence、damage、cost、steps、final。
- T10 / DeepSeek-V4-Flash：unfinished，得分 0/10，错误字段 lasers、count、target_sources、unused_safe_mounts。
