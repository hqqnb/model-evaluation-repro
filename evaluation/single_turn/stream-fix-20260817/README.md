# 流式路径修复与补跑：2026-08-17

本批次针对如流主文档《大模型评测@20260817》中仍未完成的模型测试，
排查完整响应失败、流式输出失败和上游路由异常，并在不降低推理强度的
前提下补跑。

## 结论

- Opus 5 的文本 Coding 题使用 `/v1/responses` 时会在请求转换阶段返回
  `HTTP 500 / convert_request_failed / not implemented`。将入口改为
  `/v1/chat/completions` 并保留 `reasoning_effort: max` 后，C01、C05、
  C06、C07 均成功。
- Opus 5 的部分请求还遇到上游 `HTTP 404 / upstream_error /
  bad_response_status_code`。采集器已增加针对这一明确瞬时错误的自动重试，
  不会重试确定性的参数转换错误或真正的接口不存在。
- Opus 4.8 的 R01、R03 在 2026-08-15 已有符合最高推理强度的流式成功运行，
  因此本批次复用这些成功证据，不重复消耗长请求。
- Opus 5 C08 的第一次重试持续输出但未收束；继续运行后已收到完整的
  `finish_reason: stop` 和 `[DONE]`。不过回答只包含工具调用请求，没有实际
  交付物，因此只能标记为“接口成功、交付物待复核”。

## 结果

| 模型 | 题目 | 状态 | 运行方式 | 说明 |
| --- | --- | --- | --- | --- |
| Opus 4.8 | `reasoning-r01` | success | Responses stream | 复用 2026-08-15 成功运行 |
| Opus 4.8 | `reasoning-r03` | success | Responses stream | 复用 2026-08-15 成功运行 |
| Opus 5 | `coding-c01` | success | Chat Completions stream | `reasoning_effort: max` |
| Opus 5 | `coding-c05` | success | Chat Completions stream | `reasoning_effort: max` |
| Opus 5 | `coding-c06` | success | Chat Completions stream | `reasoning_effort: max` |
| Opus 5 | `coding-c07` | success | Chat Completions stream | `reasoning_effort: max` |
| Opus 5 | `coding-c08` | success_api_review_required | Chat Completions stream | 已收到 stop；回答为工具调用请求，待交付物复核 |

接口成功只表示拿到完整模型回答，不等于评分通过。Coding 题仍需检查
交付物是否真实可运行，多模态或推理题仍需按对应评分规则复核。

## 代码修复

采集器正式配置已将 Opus 5 切换到已验证可用的
`/v1/chat/completions` 流式入口；Opus 4.8 继续使用
`/v1/responses` 流式入口。传输层仅对明确的上游瞬时 404 自动重试，
并保留每次尝试的原始响应。

相关文件：

- `runners/model-api-collector/config/models.yaml`
- `runners/model-api-collector/src/model_api_collector/transport.py`
- `runners/model-api-collector/tests/test_transport.py`

本次修复已通过采集器传输层和 SSE 测试：30 项通过。

## 如流回填边界

本批次只生成归档和回填依据，不自动覆盖如流主表。待人工完成回答内容、
Coding 交付物和评分复核后，再把最终状态、分数和链接回填到主文档。
