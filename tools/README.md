# Agent 结果发布工具

这里保存本次 Agent 测评使用过的结果整理、脱敏、人工复核和知识库发布脚本。

## 工具分类

- `generate_agent_review.py`：从运行结果生成模型级复核材料。
- `publish_agent_markdown.py`：整理和脱敏可发布的 Markdown 结果。
- `normalize_*_agent_reviews*`：修正特定模型复核内容的格式和表述。
- `update_ku_agent_results*.mjs`：将结果回填到知识库表格或文档。
- `ku_editor_guards*`：对知识库编辑操作做保护和测试。
- `agent-review-template.html`：人工复核页面模板。

## 使用边界

这些脚本中有一部分依赖本地知识库登录态、工作区路径或外部 CLI。它们被归档用于复盘和继续维护，不代表在干净 clone 中无需配置即可运行。

运行前需要：

- 检查脚本中的输入路径和输出路径；
- 使用环境变量或本地凭据管理器提供认证信息；
- 不要把 `.env`、Cookie、浏览器状态或 API Key 传入 Git；
- 先在小范围文件上验证，再执行批量更新。
