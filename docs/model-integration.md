# 模型接入

## OpenAI-compatible API

新增模型通常只需要两步：

1. 在 `configs/providers.example.yaml` 增加 Provider；
2. 在 `configs/models.example.yaml` 增加模型 ID、协议和参数。

示例：

```yaml
providers:
  example-relay:
    base_url: https://api.example.com/v1
    api_key_env: EXAMPLE_API_KEY
    protocol: chat_completions

models:
  example-model:
    provider: example-relay
    model: example-model
    protocol: chat_completions
```

先用 `/models` 或一条最小 Chat Completions 请求确认模型 ID，再运行正式题库。不要根据网页显示名称猜测 API model ID。

## 参数记录

请求中的模型 ID、温度、推理档位、流式设置、超时、重试和接口类型都要进入运行 manifest。服务端实际生效的参数如果能从响应回显，也要单独记录，不能把“请求参数”当成“上游实际参数”。

## 密钥

只使用环境变量或本地未跟踪文件。Skill 和脚本可以检查变量是否存在，但不得打印值、写入结果或提交到 Git。
