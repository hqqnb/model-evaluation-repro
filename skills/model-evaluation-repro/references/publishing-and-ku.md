# GitHub 发布与如流回填

## GitHub 统一原则

- 原始回答进入现有 `llm-evaluation-question-bank` 仓库。
- Coding 可运行页面进入现有 `llm-evaluation-previews` 仓库。
- 沿用现有 campaign、题目和模型目录，不为一次补跑新建平行仓库。
- 页面路径保持类似：

  ```text
  <campaign>/coding-cXX/<model-alias>/
  ```

- 使用仓库脚本机械提取模型原始 HTML/SVG；不得在提取阶段修代码。
- 多文件 Coding 项目保留文件结构、依赖、测试和 provenance。
- 推送后逐页回读 HTTP 状态、标题、关键交互和必要文件哈希。

单轮 Coding 预览必须从已有 question-bank 仓库运行。canonical 项目中的脚本
副本没有 `runs/<campaign>` 数据，不能直接作为发布数据源：

```bash
cd <llm-evaluation-question-bank-repo>
python3 scripts/publish_coding_previews.py \
  --campaign-id <campaign-id> \
  --preview-repo <local-preview-repo> \
  --github-repository hqqnb/llm-evaluation-previews
```

脚本只做机械提取和索引生成；多文件 Coding 项目需要先按原目录结构整理到
预览仓库，再自行执行安装、测试和浏览器检查。

发布前确认 question-bank 中已经存在：

```text
runs/<campaign-id>/results.jsonl
runs/<campaign-id>/responses/<item-id>/<model-alias>.md
```

发布后使用 Skill 审计核对 question-bank 与 preview：

```bash
python3 <canonical-repo>/skills/model-evaluation-repro/scripts/audit_model_evaluation.py \
  --repo <canonical-repo> \
  --model <model-alias> \
  --question-bank <llm-evaluation-question-bank-repo> \
  --preview-repo <llm-evaluation-previews-repo> \
  --campaign-id <campaign-id>
```

该审计验证本地 question-bank、preview metadata、源回答哈希和预览产物哈希。
它不替代 `git push` 和远端 GitHub Pages 浏览器回读；远端 URL 仍需逐页确认。

评测侧修复必须：

- 保留原始文件和哈希；
- 在 README/REVIEW/metadata 中写清修改；
- 预览页明确标注修复边界；
- 评分仍以模型原始交付为准。

## 如流操作

先加载如流 shared 与 KU Skill。文档修改前：

1. Protocol 1 读取结构化内容并保存备份。
2. Protocol 2 读取可搜索文本。
3. 精确定位目标模型×题目单元格及同题相邻格格式。
4. 生成拟修改清单，排名/评分需用户确认。

写入时：

- 尽量做 block-level 或精确节点修改；
- 禁止用旧快照覆盖最新文档；
- 保持换行，例如 `预览` 与 `答案：...` 分行；
- 分数、说明、截图和预览链接与同题其他格一致；
- 不改未确认的排名和其他模型内容。

写入后必须 Protocol 1/2 回读并检查：

- 目标文字与链接已出现；
- 旧错误文字已消失；
- 表格行列数未变化；
- 图片说明、反引号、Markdown 和换行正常；
- 该题总结、榜单和综合结论没有出现事实冲突；
- 非目标链接和单元格没有变化。

## 最终交付

最终汇总至少报告：

- 已跑题目与仍未完成题目；
- 成功、技术失败、内容失败和交付失败；
- 推理强度、协议、流式设置和 run ID；
- GitHub 原始回答与预览状态；
- 如流已回填内容及双协议回读结果；
- 用户仍需确认的分数、排名和主观结论；
- 未执行事项。
