# 新模型完整测评流程

## 0. 刷新当前基线

不要先翻历史会话。按顺序读取：

1. 如流主文档最新版 Protocol 1：保留富文本结构、表格节点和图片说明。
2. 如流主文档最新版 Protocol 2：快速搜索缺口、模型名、分数和结论。
3. `benchmark/question_bank/manifest.json`：确认当前题库版本和 28 道题范围。
4. `git status`、当前 commit 和 `evaluation/`：确认本地最新证据与未提交内容。
5. GitHub 原始回答/预览：只在需要核对已发布证据时读取。

输出一份本轮工作清单，至少包含模型、题目、如流当前状态、最新本地证据、
是否需要重跑、目标交付物和回填状态。

## 1. 本地验证

```bash
./scripts/bootstrap.sh
./scripts/smoke-test.sh
python3 scripts/validate_project.py
python3 benchmark/question_bank/validate_manifest.py
python3 skills/model-evaluation-repro/scripts/audit_model_evaluation.py --repo .
```

不联网检查未通过时，不开始付费或长时间请求。

## 2. 导出题面

单轮题从统一题库导出，禁止手工重写题面或把 rubric 拼进 prompt：

```bash
python3 benchmark/question_bank/single_turn/scripts/export_collector_prompts.py \
  --output-dir <export-dir>
```

该脚本会一次生成 `prompts-chat.jsonl`、`prompts-responses.jsonl` 和
`export.json`。根据模型 endpoint 选择对应文件：

```text
<export-dir>/prompts-chat.jsonl
<export-dir>/prompts-responses.jsonl
```

多模态题必须保留原图和顺序。

## 3. 最小探针与扩容

先用一个模型、一题、一次逻辑请求：

```bash
.venv/bin/model-api-collector run \
  --config runners/model-api-collector/config/models.yaml \
  --prompts <one-prompt.jsonl> \
  --models <model-alias> \
  --repeat 1 \
  --max-attempts 3
```

流式模型显式加入：

```bash
--delivery-mode stream
```

检查 `run.json`、`results.jsonl`、`request.json`、原始响应、`response.md` 和
`metadata.json`。确认后再扩大题目范围；新模型默认仍从低并发开始。

## 4. 四类题分流

### 推理

- 保存完整答案和必要推导。
- 用参考答案或确定性脚本核对最终值。
- “有回答”不等于“答对”；不要把格式问题误判为未作答。

### Coding

- 单文件 HTML/SVG 可机械提取到预览目录。
- 多文件项目或模型提出工具调用时，必须执行工具循环直到真实文件落盘。
- 运行项目自带测试、题目黑盒测试和页面实机检查。
- 保留原始交付；不要为了让页面能跑而静默修改模型代码。

### 多模态

- 在 `request.json` 中确认图片字段和全部附件真实发送。
- 旧的“未收到图片”结论只能由对应旧请求支持，不能覆盖新的成功请求。
- 按最新版参考答案逐项核对，不凭记忆补充或删除识别项。

### Agent

- 使用 `third_party/automationbench` 的完整工具闭环。
- 先做模型/协议 preflight，再跑单题，最后跑 T01-T08。
- 保存工具轨迹、模型轮数、最终状态、逐项断言、部分得分、严格通过和技术失败。
- 单轮 API 中出现工具调用文本不算 Agent 完成。

正式 Agent 批次使用 pinned manifest，不要用第三方 README 的默认全量任务
替代本项目的 T01-T08：

```bash
cd third_party/automationbench
uv sync
cp -n configs/agent.env.example configs/.env.local
# 在 configs/.env.local 中填写本轮密钥；该文件被 Git 忽略。

uv run python -m automationbench.scripts.formal_agent_suite \
  --manifest configs/agent-suite-v1.1-tool-errors-noleak-20260815.json \
  --models <model-run-id> \
  --preflight-only

uv run python -m automationbench.scripts.formal_agent_suite \
  --manifest configs/agent-suite-v1.1-tool-errors-noleak-20260815.json \
  --models <model-run-id> \
  --resume \
  --technical-retries 2 \
  --timeout-seconds 14400 \
  --isolate-tasks
```

新模型先复制 manifest 中的模型配置并设置实际 API/推理档位，再执行
`--preflight-only`。不要改写已经用于历史结果的模型记录；为新模型新增唯一
`run_id`，并用 `--models <model-run-id>` 只运行本轮目标。预检失败时只归档为
技术失败，不进入能力排名。

## 5. 结果归档

每个正式批次至少保存：

- 运行日期、run ID、题库版本和 Git commit；
- Provider、model ID、endpoint、协议和 delivery mode；
- 请求参数、上游回显、超时、重试和重复次数；
- 原始请求、原始响应、最终文本和错误；
- Coding 交付物与测试；Agent 轨迹与状态；
- 逐题评分、复核说明和发布链接。

新成功结果与旧失败结果同时保留，用时间和 run ID 区分。不要覆盖历史错误证据。

## 6. 审核、发布和回填

1. 生成 Markdown 审核稿。
2. 用户确认 Coding 分数、主观判断和排名。
3. 把原始回答归档到现有 question-bank 仓库。
4. 把 Coding 交付物发布到现有 previews 仓库。
5. 回读 GitHub/Pages，确认 URL 与本地最终文件一致。
6. 按原格子格式回填如流。
7. Protocol 1/2 双回读，确认表格结构、链接、目标单元格和总结。
8. 更新仓库 README/工作总览与 Knowledge OS 项目状态。

正式结束前运行一次全链路审计：

```bash
python3 skills/model-evaluation-repro/scripts/audit_model_evaluation.py \
  --repo . \
  --model <model-alias> \
  --expected-reasoning-effort <highest-value> \
  --run-dir <single-turn-run> \
  --agent-summary <agent-summary.json> \
  --question-bank <question-bank-repo> \
  --preview-repo <preview-repo> \
  --campaign-id <campaign-id> \
  --scan-root <published-or-archived-artifacts>
```

审计中的 `effective_reasoning_unconfirmed` 是“上游未回显，无法确认实际生效值”
的警告，不等于请求失败；`agent_ranking_order` 需要人工核对正式排名规则。
