# 统一大模型能力测评题库

这里是整个项目唯一的正式题库入口。题库不是几套彼此独立的 benchmark，而是一套统一的测评内容，按四种能力组织：

- **推理**：面对多重条件、数字、规则和不完整信息，模型能否得出正确结论。
- **Coding**：模型能否把要求转化为可运行、可验证的代码，而不是只写出一段看起来合理的代码。
- **多模态**：模型能否从固定图片中准确提取信息，并根据图片完成判断或推理。
- **Agent**：模型能否在工具、业务状态和用户约束下，经过多轮操作真正完成任务。

## 当前版本

当前统一快照为 `model-evaluation-20260805`，共 28 道题：

| 能力 | 题量 | 主要材料 |
| --- | ---: | --- |
| 推理 | 8 | `single_turn/dataset/prompts.json` |
| Coding | 8 | `single_turn/dataset/prompts.json` |
| 多模态 | 4 | `single_turn/dataset/prompts.json` 与 `single_turn/assets/` |
| Agent | 8 | `agent/tasks.md` |

题库的总范围、题目编号和各类材料路径以 `manifest.json` 为准。`single_turn/` 和 `agent/` 是同一套题库的不同任务形态，不代表两个项目。

## 题库材料

- `single_turn/dataset/prompts.json`：推理、Coding、多模态题目实际下发给模型的版本。
- `single_turn/rubrics/rubrics.json`：对应评分信息和人工评审重点，不能下发给被测模型。
- `single_turn/assets/`：多模态题目使用的固定素材。
- `single_turn/source_material/`：题目说明、内部答案、Coding 检查脚本和来源材料。
- `agent/tasks.md`：8 道 Agent 题目的场景、目标、工具要求、评分规则和严重错误边界。
- `agent/api_compatibility.md`：当前 Agent 题目与执行环境的适配情况。
- `archive/`：曾经参与设计或预跑的材料，只用于追溯和比较，不作为当前快照的默认入口。

## 设计方式

每道题都应同时说明四件事：

1. 模型需要完成的真实目标；
2. 不能违反的条件和安全边界；
3. 可以被复核的结果或证据；
4. 结果如何转换成分数。

因此，题库不只保存题面。题目、素材、评分标准、确定性测试、模拟环境、结果证据和历史版本共同构成一套完整测评。

## 校验

单轮题库的结构校验：

```bash
python3 benchmark/question_bank/single_turn/scripts/validate_dataset.py
```

仓库级校验：

```bash
./scripts/smoke-test.sh
```
