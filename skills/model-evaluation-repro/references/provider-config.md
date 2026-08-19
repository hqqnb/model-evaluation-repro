# Provider 与模型接入

## 先确认，不要猜

新增模型前确认：

- API model ID，不使用网页展示名代替；
- Provider base URL 和可用 endpoint；
- 协议：`chat_completions`、`responses` 或 `anthropic`；
- 是否必须流式；
- 该模型在当前 Provider 上的最高推理强度值；
- 多模态图片字段是否被 Provider 接受；
- 密钥环境变量名。

最高推理强度是 Provider/模型相关值，例如当前归档中出现过 `max` 和 `xhigh`。
不要把某个模型的取值机械复制给另一个模型。使用一条最小请求确认参数被接受，
并同时记录请求值和上游回显值。

## 配置位置

项目正式采集配置通常位于：

```text
runners/model-api-collector/config/models.yaml
```

可公开的示例配置位于：

```text
configs/providers.example.yaml
configs/models.example.yaml
```

模型配置至少记录：

```yaml
models:
  new-model:
    model: exact-upstream-model-id
    endpoint: /v1/chat/completions
    stream: true
    parameters:
      temperature: 0
      reasoning_effort: highest-supported-value
```

Provider 密钥只通过环境变量或本地未跟踪配置提供。任何脚本只能报告变量
“存在/不存在”，不能输出其值。

示例文件必须保持脱敏：

```text
configs/agent.env.example   # 只留空值或占位符，可提交
configs/.env.local          # 真实值，必须被 Git 忽略
```

若发现真实密钥已经进入提交历史，仅清空当前文件不等于安全恢复；必须旋转密钥，
是否重写远端历史需由用户确认。

## 接入门槛

1. 本地 smoke test 通过。
2. 一条无害文本题成功。
3. 若测多模态，再单独验证图片真实进入 `request.json`。
4. 若测长 Coding，确认流式不会断流且最终响应完整。
5. 若测 Agent，确认工具 schema、工具调用解析和 tool result 回传可用。
6. 保存 endpoint、协议、stream、推理强度、超时和重试策略。

当前已知经验不能泛化成永远正确的规则：某模型在 `responses` 转换失败时，
`chat/completions` 可能可用；另一个模型可能恰好相反。因此每次新模型接入
都需要最小探针，而不是按品牌猜协议。
