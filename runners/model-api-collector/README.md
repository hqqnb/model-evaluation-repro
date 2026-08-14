# 模型 API 原始回答采集器

这个工具通过 OneAPI 直接调用模型，自动保存原始回答、请求参数、耗时、Token
用量和错误信息。它不会调用 Codex、搜索工具或其他 Agent 框架，也不会修改题目。

## 1. 初始化

在项目目录运行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[test]"
```

所有依赖都安装在当前项目的 `.venv` 中，不影响系统 Python。

## 2. 配置 OneAPI

创建本机配置：

```bash
cp .env.example .env
```

编辑 `.env`：

```dotenv
ONEAPI_BASE_URL=https://your-oneapi-host.example.com
ONEAPI_API_KEY=your-local-key
ONEAPI_TIMEOUT_SECONDS=120
ONEAPI_COMPLETE_TIMEOUT_SECONDS=600
ONEAPI_MAX_ATTEMPTS=3
```

`ONEAPI_BASE_URL` 填服务器根地址，不要在末尾添加 `/v1`。密钥只保存在本机
`.env`，该文件已被 Git 忽略，也不会写入测评结果。

## 3. 配置模型

```bash
cp config/models.example.yaml config/models.yaml
```

将 `model` 改成 OneAPI 中实际使用的模型 ID：

```yaml
models:
  kimi:
    model: your-kimi-model-id
    stream: false
    parameters:
      temperature: 0
  another-model:
    model: another-model-id
    stream: false
    parameters:
      temperature: 0
```

模型 ID、是否流式以及全部生成参数都会进入运行记录。不要在
`parameters` 中填写 `model`、`messages`、`input` 或 `stream`。

不同 API 服务商使用不同密钥时，分别创建独立环境文件。例如 Qwen：

```dotenv
ONEAPI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode
ONEAPI_API_KEY=your-qwen-api-key
ONEAPI_TIMEOUT_SECONDS=120
```

对应模型配置位于 `config/qwen.yaml`。运行时通过
`--env-file .env.qwen` 指定 Qwen 的独立密钥，不会覆盖 OneAPI 配置。

`qwen3.8-max` 的思考模式最低温度为 `0.6`，配置中保留该服务端约束。跨模型
比较时应记录实际参数，并通过重复运行衡量稳定性，而不是把服务端不支持的
`temperature: 0` 当作已生效。

正式测评统一请求各入口支持的最高推理档位：`glm-5.2`、`gpt-5.6-sol`、
`Opus 5`、`Opus 4.8`、`DeepSeek-V4`、`Kimi K3` 和 Qwen 使用
`reasoning_effort: max`；`gpt-5.5` 使用其入口支持的最高档位
`reasoning_effort: xhigh`；Hy3 当前入口的最高档位为
`reasoning_effort: high`。这些参数会原样写入实际请求和运行记录，不会通过
系统提示词或额外标记改变题目。

Kimi K3 使用官方 Kimi API 开放平台的独立密钥：

```dotenv
ONEAPI_BASE_URL=https://api.moonshot.cn
ONEAPI_API_KEY=your-kimi-api-key
ONEAPI_TIMEOUT_SECONDS=300
```

对应模型配置位于 `config/kimi.yaml`，模型 ID 为 `kimi-k3`。K3 始终启用
推理，采集器使用原生默认的 `reasoning_effort: max`，不声明工具、联网搜索或
Agent 能力。Kimi Code 和 Kimi 会员的密钥不能代替开放平台 API Key。

腾讯混元 Hy3 使用 TokenHub 的独立 API Key：

```dotenv
ONEAPI_BASE_URL=https://tokenhub.tencentmaas.com
ONEAPI_API_KEY=your-tokenhub-api-key
ONEAPI_TIMEOUT_SECONDS=300
```

对应模型配置位于 `config/hy3.yaml`，正式版模型 ID 为 `hy3`。测评显式使用
`reasoning_effort: high` 和 `preserved_thinking: false`，不声明联网搜索、
工具或 Agent；流式请求开启 `stream_options.include_usage` 以保存 Token 用量。
上面的地址适用于腾讯云中国站；国际站 Key 需要改用新加坡接口。

`Opus 5` 和 `Opus 4.8` 使用公司提供的 OneAPI `/v1/responses` 中转，不要求
Anthropic 官方 Key。配置显式请求 `reasoning_effort: max`，但不会添加系统提示词、
工具调用或 Agent 循环。采集器会把题目原样放入 Responses API 的 `input` 字段。

## 4. 准备题目

题目使用 JSONL 格式，每行一道题：

```json
{"id":"translation-001","title":"Translation","messages":[{"role":"user","content":"Translate this sentence into Chinese: The meeting starts at nine."}],"tags":["translation"]}
```

Chat Completions 模型使用 `messages`，Responses API 模型使用 `input`；两者
都直接来自题目文件，采集器不会添加系统提示词。标准 OpenAI 多模态 `content`
数组也会原样透传。Word、PDF、音视频不会被自动解析，以免将外部工具能力混入
模型能力。

## 5. 运行前检查

```bash
.venv/bin/model-api-collector validate \
  --config config/models.yaml \
  --prompts prompts/example.jsonl
```

该命令只检查配置和题目，不会请求模型。

需要同时验证请求体构造时，可以运行：

```bash
.venv/bin/model-api-collector preflight \
  --config config/models.yaml \
  --prompts prompts/example.jsonl \
  --models all
```

`preflight` 只构造本地请求，不发送 API 请求。

## 6. 开始采集

运行一个模型：

```bash
.venv/bin/model-api-collector run \
  --config config/models.yaml \
  --prompts prompts/example.jsonl \
  --models kimi
```

默认遵循模型配置中的 `stream` 设置。当前正式配置中 Opus 5 和 Opus 4.8
默认流式，其他模型默认使用完整响应。需要统一使用完整响应时：

```bash
.venv/bin/model-api-collector run \
  --config config/models.yaml \
  --prompts prompts/example.jsonl \
  --models all \
  --delivery-mode complete
```

运行全部模型：

```bash
.venv/bin/model-api-collector run \
  --config config/models.yaml \
  --prompts prompts/example.jsonl \
  --models all
```

每道题默认独立运行两次，用于交叉验证：

```bash
.venv/bin/model-api-collector run \
  --config config/models.yaml \
  --prompts prompts/example.jsonl \
  --models all
```

显式指定重复次数：

```bash
.venv/bin/model-api-collector run \
  --config config/models.yaml \
  --prompts prompts/example.jsonl \
  --models all \
  --repeat 3
```

`--repeat 1` 可用于单次专项运行。两遍测试是两次独立逻辑请求，题目和请求
参数保持一致；两次结果分别保留在 `results.jsonl` 和各自的
`requests/<request-id>/` 目录中，不会在模型输入中添加“第几遍”等标记。
一次逻辑请求内部因网络错误、超时、限流或不完整响应触发的 retry 不算新增
重复结果，也不会额外增加正常结果行。

批量任务默认顺序运行。请求失败后会继续下一项。网络错误、超时、429/5xx、
断流和不完整响应默认最多尝试三次；可用 `--max-attempts` 覆盖本次运行。

除 Opus 5 和 Opus 4.8 按模型配置默认使用流式外，其他模型如需测量首字延迟或推理片段，
可以显式切换为流式模式：

```bash
.venv/bin/model-api-collector run \
  --config config/models.yaml \
  --prompts prompts/example.jsonl \
  --models all \
  --delivery-mode stream
```

## 7. 查看结果

每次运行会生成：

```text
runs/<run-id>/
  run.json
  results.jsonl
  summary.csv
  requests/<request-id>/
    request.json
    response-headers.json
    response.sse 或 response.json
    response.attempt-*.sse 或 response.attempt-*.json（内部重试记录）
    response.md
    metadata.json
    error.json（仅失败时）
```

- `request.json` 是实际发送的请求。
- `response.sse` 或 `response.json` 是收到的原始响应正文。
- `response.md` 是还原后的模型最终回答。
- `metadata.json` 包含模型、题目、参数、状态、耗时和 Token 用量。
- `metadata.json` 中的 `requested_parameters` 是本地实际发送的参数，
  `effective_parameters` 是上游响应回显的参数；两者不一致时不能把请求值
  当成中转实际生效值。
- `summary.csv` 可直接用于表格比较。
- 默认每道题保留两条独立结果；`--repeat N` 时保留 N 条结果。
- 一道题的一次逻辑请求只写入一条结果；中间重试不会生成额外结果行。
- 半截回答、空回答、未完成响应不会被当作成功答案。

## 8. 耗时口径

- 响应头延迟：从开始请求到收到 HTTP 响应头。
- 首事件延迟：从开始请求到收到第一个有效 SSE 数据事件。
- 首推理延迟：从开始请求到收到第一个非空隐藏推理片段；模型不返回推理时为空。
- 首字延迟：从开始请求到收到第一个非空、用户可见的最终回答文本。
- 总耗时：从开始请求到响应完成或失败。

非流式请求没有首事件和首字延迟，只记录响应头延迟与总耗时。

## 9. 能力边界

采集器保证本机请求不经过 Codex、网页端或其他 Agent，不启用工具、记忆或
题目改写。自动重试只用于恢复传输层失败，不会拼接多个半截回答，也不会改变题目
和请求内容。

OneAPI 后面的供应商路由、排队和协议转换无法从本机完全观察。因此结果能够
证明“发送给 OneAPI 的请求一致且无 Agent 增强”，但不能证明供应商服务内部
没有进行适配。

不同模型经过不同 API 网关时，能力题答案仍可按统一标准比较，但首字延迟和总耗时
同时包含网关、地域与网络链路差异，不应直接作为模型推理速度排名。

## 10. 本地测试

```bash
.venv/bin/python -m pytest -q
```

测试使用本地模拟接口，不会消耗真实 API，也不需要真实密钥。
