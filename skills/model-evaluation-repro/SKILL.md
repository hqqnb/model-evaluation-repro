---
name: model-evaluation-repro
description: Use when adding or testing a model in the canonical evaluation project, including provider setup, full or gap runs across reasoning/Coding/multimodal/Agent tasks, highest-reasoning configuration, failure recovery, deliverable review, scoring, GitHub previews, KU backfill, and final audit.
---

# Model Evaluation Repro

把新增模型从接入、运行、复核、发布到如流回填完整走通。不要依赖历史会话
记忆；每次都从实时如流文档、canonical 仓库和已发布证据重建当前状态。

## 来源优先级

1. 如流主文档最新版：当前表格、缺口、已发布结论和单元格格式。
2. 仓库题库 manifest、题面、素材和 rubric：本次运行与评分输入。
3. 仓库原始运行、交付物、测试和审核稿：评分证据。
4. GitHub 原始回答与 Pages：对外可访问证据和 Coding 预览。
5. 历史会话、旧失败文件和人工记忆只能作为定位线索，不能直接定稿。

默认 canonical 仓库为 `/Users/zay/Documents/模型测评项目`；若不存在，先定位
具有相同目录结构的干净 clone。先运行：

```bash
python3 skills/model-evaluation-repro/scripts/audit_model_evaluation.py --repo <repo>
./scripts/smoke-test.sh
```

## 必走流程

1. **刷新基线**：实时读取如流主文档 Protocol 1 和 Protocol 2；记录文档 ID、
   发布时间、当前缺口和用户已确认的结论。不要沿用旧审核稿中的“未跑”状态。
2. **固定版本**：记录 Git commit、题库 `bank_id`、题目 ID、素材、rubric 和
   运行日期。工作区有未提交内容时不得覆盖或混入无关修改。
3. **接入模型**：核实 API model ID、endpoint、协议、是否流式、最高可用推理
   强度和密钥环境变量。只检查密钥是否存在，禁止打印值。
4. **最小探针**：先跑一条无害题，确认鉴权、模型 ID、协议、流式解析和结果
   归档。通过后再从单题低并发扩大。
5. **运行题库**：单轮题走 `model-api-collector`；Agent T01-T08 必须走真实
   工具闭环和状态断言。具体命令与题型分流见
   `references/end-to-end-workflow.md`。
6. **失败恢复**：保留每次原始错误；先查协议和传输，再查模型能力。完整响应
   失败时可改流式，已验证的 endpoint 失败时可切换兼容协议，但不得降低推理
   强度或改变题面。见 `references/failure-recovery.md`。
7. **证据复核**：API `success` 只代表收到完整响应。推理核答案，多模态核图片
   确实发送，Coding 核真实可运行交付物，Agent 核工具轨迹和最终状态。
8. **先审后填**：先把所有拟评分和拟回填文字写入一份 Markdown 审核稿。
   Coding 评分、主观结论和排名必须经用户确认后才能写入如流。
9. **统一发布**：所有 Coding 交付物放入现有预览仓库和既有目录结构，不新建
   平行仓库。原始交付与评测侧修复版必须分开标注，修复版不能计入原始得分。
10. **回填与回读**：按同题其他格子的格式写入分数、结论和链接。发布后同时
    用 Protocol 1/2 回读，核对目标单元格、表格结构、链接和结论未被误改。
11. **收尾审计**：对正式 run 使用：

    ```bash
    python3 skills/model-evaluation-repro/scripts/audit_model_evaluation.py \
      --repo <repo> \
      --model <alias> \
      --expected-reasoning-effort <highest-value> \
      --run-dir <run-dir> \
      --agent-summary <formal-suite-summary.json> \
      --question-bank <question-bank-repo> \
      --preview-repo <preview-repo> \
      --campaign-id <campaign-id> \
      --scan-root <published-artifacts>
    ```

## 关键判定

- `HTTP 200`、`finish_reason=stop`、有文本、答案正确、形成可交付代码是不同层级。
- 新成功运行可以替代旧限流/空文件结论，但必须保留两次运行的日期与来源。
- Coding 回答若只有 `execute_bash`/`fs_write` 等工具调用请求，尚未形成交付物；
  需要继续工具循环，直到文件真实落盘并可运行。
- 不把文本式工具规划当成 Agent 结果；Agent 必须执行工具、返回结果、改变状态
  并完成断言。
- 不把 API、网关、超时、限流或图片未发送问题归因成模型能力失败。
- 请求参数和上游回显不一致时，分别记录 `requested_parameters` 和
  `effective_parameters`。
- `requested_parameters.reasoning_effort` 只能证明本地请求值；若上游有
  `effective_parameters` 回显，必须单独核对，未回显时标记为“无法确认实际生效值”。
- 用户未确认的排名、并列关系和主观评分保持不动；客观笔误和错误归因需有证据
  后修正。

## 按需加载

- Provider、模型 ID、最高推理强度：`references/provider-config.md`
- 完整运行顺序与题型分流：`references/end-to-end-workflow.md`
- 错误诊断和续跑：`references/failure-recovery.md`
- 评分与 Coding/Agent 复核：`references/review-and-scoring.md`
- GitHub 发布与如流回填：`references/publishing-and-ku.md`

## 安全边界

- 禁止在输出、日志、Markdown、Git 或如流中保存 API Key、Cookie、Bearer
  Token、浏览器登录态或 `.env`。
- `*.example` 只能保留空值或明确占位符；真实密钥放在被 Git 忽略的
  `.env.local`，仓库审计会把非占位符示例密钥视为错误。
- 内部参考答案和 rubric 不得发送给被测模型。
- 不修改模型原始回答以提高得分；机械提取与评测侧修复都必须留 provenance。
- 不用旧文件存在与否判断最新版结果，必须比较运行时间、run ID 和证据完整性。

## 不自动替代人工的环节

- Coding 的视觉、交互和真实可玩性验收；
- 主观评分、硬性分数边界解释、榜单顺序和并列关系；
- 如流最终写入前的用户确认；
- Git push、GitHub Pages 部署完成和公网预览的浏览器回读；
- Provider 未回显时的实际推理档位确认；
- 已泄露凭据的旋转和 Git 历史清理。
