# Agent Benchmark Integrity and Efficiency

## Goal

修复 formal eight-task Agent benchmark 中会泄露答案、替模型做判断、无法记录错误行为、评分过弱和效率不佳的问题，并用新批次重新运行评测。

## Scope

- 保留 T01-T08 编号、题面和整体任务覆盖。
- 模型可见工具只返回业务事实，不返回 `expected_*`、隐藏 oracle、标准答案标签或异常答案。
- 错误动作必须留下可评分的尝试轨迹；工具可以阻止危险副作用，但不能用具体正确分类替模型决策。
- 银行业务敏感操作必须先完成身份验证。
- 加强 T03、T05、T06、T08 的结构化交付物和过程断言。
- 用批量读取、去重读取和合理步骤预算减少无意义工具循环，不牺牲任务覆盖。
- 修复后使用新的 benchmark 版本和新批次目录，旧结果只作为历史基线。

## Test-First Cases

1. T01/T02/T08 的读取工具不返回隐藏判定字段。
2. T05 的 source validation 不返回 `known_anomalies`。
3. T01/T02/T08 的非法动作会写入 `*_invalid_attempt` 轨迹，并返回中性错误。
4. T07 的 transfer review 和 limit increase 在未验证身份时不会创建业务请求，但会记录越权尝试。
5. workspace artifact 校验会拒绝内容为空、大小不一致、扩展名与结构不匹配的交付物。
6. T05 读取计数按不同路径计数，重复读取同一文件不能满足覆盖要求。

## Implementation

### Data isolation

- 在任务初始状态中将后台 oracle 与业务事实分离。
- 读取工具使用显式字段白名单；必要时由工具根据业务事实计算派生属性，但不返回标准答案字段。
- `tool_log` 保留参数审计，API key 只在日志中脱敏。

### Action semantics

- 业务动作不根据隐藏 `eligible`、`needs_human`、`closed` 等字段静默拦截。
- 工具只校验资源是否存在、输入格式和真实副作用安全边界。
- 对策略不允许的动作记录 `invalid_attempt`，返回 `operation_rejected`，不返回正确处理结果。
- 隐藏 oracle 由评分器读取，不进入模型上下文。

### Assertions

- 增加动作顺序、不同文件覆盖、隐藏字段泄露和无效尝试断言。
- 对 T03 验证预算明细、行程条目和约束一致性。
- 对 T05 验证发现内容与源文件证据、任务日期格式和客户 ID。
- 对 T06 验证真正受影响的任务、日期、状态、依赖和无关任务保持不变。
- 对 workspace artifact 按 MIME/扩展名做最小结构解析。

### Efficiency

- 增加一次性读取元数据和批量事实读取能力，避免重复拉取相同大对象。
- 工具结果减少重复状态和隐藏字段。
- runner 采用单模型单题 smoke -> 单模型全题 -> 低并发多模型的波次流程。
- 记录每题工具调用数、模型轮数、token、耗时、技术失败和重试次数。

## Verification

1. 运行新增失败测试，确认旧实现确实被捕获。
2. 修改实现后运行 benchmark 专项测试和完整本地测试。
3. 运行 oracle trajectory，确保每题仍可达到满分。
4. 做单模型单题 API smoke test。
5. 使用新版本 manifest 先低并发重跑，再扩展并发。
6. 生成修复前后效率、严格通过率、技术失败率和排名稳定性对比。
