# 项目架构

```text
configs/
  Provider 和模型注册
        |
        v
benchmark/ ---> runners/ ---> evaluation/
题面/状态/断言    API/Agent执行     标准结果/报告
        ^                              |
        |                              v
      tests <---------------------- examples
```

## Provider 层

Provider 配置描述上游地址、协议和 API Key 环境变量。模型配置只描述模型 ID 和请求参数。这样同一题库可以切换不同上游，而不会把密钥或账号信息写进题库。

## Runner 层

- `model-api-collector`：一次请求、原始响应、延迟和 Token 归档。
- `agent-runner`：预留多轮工具调用和环境状态执行入口。
- `third_party/automationbench`：固定版本的外部 Agent 环境，需遵守其许可证和版本说明。

## Evaluation 层

评分器分为确定性评分、黑盒测试和状态断言三类。人工评审可以作为补充，但必须把“人工判断”和“机器证据”区分记录。
