# 模型测评项目

这是一个用于复现大模型与 Agent 能力测评的私有项目。仓库的目标不是保存某台电脑上的临时运行结果，而是让另一位研究者能够：

1. 理解我们为什么这样设计题库和评分方法；
2. 在自己的机器上安装依赖；
3. 配置自己的模型 API Key；
4. 先运行不联网的本地校验，再执行一次最小 API smoke test；
5. 运行指定题库并获得结构化结果；
6. 根据结果文件复核模型回答、工具轨迹和评分。

## 测评链路

项目包含两类不同的测评，不应混为一个分数：

```text
单轮模型测评：
题库 -> API 请求 -> 原始回答 -> 结果归档 -> 人工或确定性评分

Agent 测评：
任务题面 -> 工具定义 -> 模拟环境 -> 多轮模型调用
       -> 工具执行 -> 环境状态变化 -> 断言评分 -> 完整轨迹
```

`model-api-collector` 适合采集一次模型回答、推理内容、Token 和耗时；它不会执行模型返回的工具调用。Agent 测评使用 AutomationBench 风格的执行闭环，只有工具执行和最终状态断言都存在时，结果才可以解释为 Agent 能力。

## 项目结构

```text
benchmark/
  curated-bank/       推理、Coding、多模态题库与确定性评分脚本
  collector-bank/     API 采集题库、Rubrics 和多模态素材
  agent_benchmark/    Agent/推理题库、评分器和校验器
runners/
  model-api-collector/ 一次请求模型回答采集器
third_party/
  automationbench/    固定版本的 Agent 评测依赖，待上游版本审查
evaluation/           统一结果和报告目录
configs/              Provider 与模型配置示例
scripts/              环境初始化、校验、smoke test 和运行入口
docs/                 方法论、架构、复现和评分说明
examples/             脱敏示例输入与结果
inventory/            从旧目录归并到本项目的来源记录
```

## 快速开始

### 1. 初始化本地环境

```bash
./scripts/bootstrap.sh
cp .env.example .env.local
```

默认初始化会安装根目录工具和 API 采集器。AutomationBench 需要 Python 3.13 及其独立依赖，如需安装：

```bash
INSTALL_AUTOMATIONBENCH=1 ./scripts/bootstrap.sh
```

### 2. 只做本地校验

这一步不访问任何模型 API：

```bash
./scripts/smoke-test.sh
```

它会检查：

- Provider 和模型配置格式；
- Agent 题库的题目、分值和答案一致性；
- 多模态题库的素材引用；
- Curated bank 的数据完整性。

### 3. 配置模型

复制并编辑：

```text
configs/providers.example.yaml
configs/models.example.yaml
```

例如 `qwen3.8-max` 的配置使用：

```yaml
provider: lingzhi
base_url: https://lingzhi.agibot.com/v1
model: qwen3.8-max
api_key_env: LINGZHI_API_KEY
protocol: chat_completions
```

API Key 只放在本地环境变量中：

```bash
export LINGZHI_API_KEY='your-local-key'
```

不要把真实 Key 写进 YAML、README、运行结果或 Git 提交。

### 4. 运行最小测评

```bash
ENV_FILE=.env.local \
CONFIG=runners/model-api-collector/config/qwen.yaml \
./scripts/run-evaluation.sh qwen3.8-max
```

这个入口默认只运行 `prompts/example.jsonl` 中的一道无害题、一次请求。确认 API、模型 ID 和费用保护都正确后，再切换到正式题库。

## 结果与复现

每次运行至少应记录：

- Provider、Base URL 和模型 ID；
- 题库或 manifest 版本；
- 实际请求参数和协议；
- 请求时间、响应时间和 Token；
- 原始响应和最终回答；
- Agent 的工具调用、工具返回、最终环境状态；
- 每条断言的结果、部分得分和严格通过结果；
- 错误、重试次数和上游响应状态。

完整复现说明见：

- [方法论](docs/methodology.md)
- [架构](docs/architecture.md)
- [复现指南](docs/reproduction.md)
- [模型接入](docs/model-integration.md)
- [评分说明](docs/scoring.md)

## 安全边界

本仓库是私有仓库，但仍不提交：

- API Key、Cookie、浏览器登录态和本机 `.env`；
- `.venv`、`node_modules`、缓存和临时日志；
- 未审核的内部业务数据；
- 大量历史运行结果和含个人信息的模型输出。

原始历史目录不会因为本项目建立而自动删除。`inventory/source-manifest.json` 记录了复制来源、目标位置和排除理由。

## 复现限制

固定题库、评分代码和运行参数可以复现测评流程；但模型输出不一定逐字一致。上游模型版本、服务端策略、限流、价格、联网数据和第三方依赖更新都会造成差异。因此历史结果必须同时保存运行 manifest 和上游版本信息，不能只保存一个总分。
