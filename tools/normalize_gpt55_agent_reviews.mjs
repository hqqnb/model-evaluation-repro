#!/usr/bin/env node

import fs from "node:fs";

const outputPath = process.argv[2];
if (!outputPath) {
  throw new Error("Usage: normalize_gpt55_agent_reviews.mjs <output-path>");
}

const summaryPath =
  process.env.AGENT_SUMMARY_PATH ||
  "evaluation/agent/model_review_summary_20260815.md";

const scores = [9.5, 9.4, 9.4, 8.8, 9.4, 9.5, 9.4, 8.4];
const reviews = [
  "完整处理 6 笔退款申请，正确完成结果登记、邮件草稿、财务升级、工单回复和整体汇总，未执行实际退款或发送外部邮件。",
  "正确区分可安排、不可安排和待补充信息的 Demo 申请，完成排期、通知与汇总，未重复创建安排。",
  "三日行程满足预算、园区、指定项目、角色用餐、行程节奏和结束时间等约束，并通过约束检查。",
  "完成 Key 使用说明、数据获取、日周月分析、质量检查及三个交付文件，但最终交付说明不够完整。",
  "完成多文件读取、数据质量检查和两份报告交付，保留原始数据，并正确区分相关性和因果关系。",
  "只调整受延期影响的任务链，保留 marketing 和 training 原计划，并完成风险、状态、恢复计划和内部通知更新。",
  "完成必要信息收集与身份验证，分别处理转账退回和限额调整，并清楚区分已提交和待审核状态。",
  "正确完成发票核对、状态登记、内部待办和中断恢复，未重复执行已有动作，但遗漏一封供应商邮件草稿。",
];

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  input += chunk;
});

function textOf(node) {
  if (!node || typeof node !== "object") return "";
  if (typeof node.text === "string") return node.text;
  if (Array.isArray(node)) return node.map(textOf).join("");
  return Object.values(node).map(textOf).join("");
}

function findAll(node, predicate, output = []) {
  if (node && typeof node === "object") {
    if (predicate(node)) output.push(node);
    for (const value of Object.values(node)) {
      findAll(value, predicate, output);
    }
  }
  return output;
}

function updateSummary() {
  const lines = fs.readFileSync(summaryPath, "utf8").split("\n");
  let changed = 0;

  const updated = lines.map((line) => {
    if (!/^\| \d+ /.test(line)) return line;
    const cells = line.split("|").slice(1, -1).map((cell) => cell.trim());
    if (cells.length !== 14) return line;

    const taskIndex = Number(cells[0]) - 1;
    if (taskIndex < 0 || taskIndex >= scores.length) return line;
    const link = cells[12].match(
      /\[完整交互回答\]\(https:\/\/github\.com\/hqqnb\/llm-evaluation-question-bank\/blob\/main\/runs\/20260814-agent\/responses\/agent-t\d{2}\/gpt-5\.5\.md\)/,
    )?.[0];
    if (!link) {
      throw new Error(`GPT-5.5 summary link not found for T${taskIndex + 1}`);
    }

    cells[12] =
      `评分：${scores[taskIndex].toFixed(1)}分<br/>` +
      `${reviews[taskIndex]}<br/>${link}`;
    changed += 1;
    return `| ${cells.join(" | ")} |`;
  });

  if (changed !== 8) {
    throw new Error(`Expected 8 summary rows, updated ${changed}`);
  }
  fs.writeFileSync(summaryPath, `${updated.join("\n").replace(/\n+$/, "")}\n`);
}

function main() {
  const current = JSON.parse(input);
  const content = current?.data?.result?.content;
  if (!Array.isArray(content)) {
    throw new Error("The query-content response has no editable content.");
  }

  const table = findAll(content, (node) => node.type === "table")[0];
  if (!table) throw new Error("Main evaluation table not found.");
  const categoryIndex = table.children.findIndex((row) =>
    textOf(row.children?.[0]).includes("类别三：Agent能力"),
  );
  if (categoryIndex < 0) throw new Error("Agent category row not found.");

  const updated = structuredClone(content);
  const updatedTable = findAll(updated, (node) => node.type === "table")[0];
  const changed = [];

  for (let i = 0; i < scores.length; i += 1) {
    const cell = updatedTable.children[categoryIndex + i + 1].children?.[12];
    if (!cell) throw new Error(`GPT-5.5 cell not found for T${i + 1}`);
    const paragraphs = cell.children.filter((child) => child.type === "paragraph");
    const scoreParagraph = paragraphs.find((child) =>
      textOf(child).includes("评分："),
    );
    const reviewParagraph = paragraphs.find((child) => {
      const value = textOf(child);
      return value && !value.includes("评分：") && !value.includes("完整交互预览");
    });
    if (!scoreParagraph || !reviewParagraph) {
      throw new Error(`GPT-5.5 review structure not found for T${i + 1}`);
    }
    scoreParagraph.children = [{ text: `评分：${scores[i].toFixed(1)}分` }];
    reviewParagraph.children = [{ text: reviews[i] }];
    changed.push(`T${String(i + 1).padStart(2, "0")}`);
  }

  const card = updated.find((node) => node.type === "card");
  if (!card) throw new Error("Editable card not found.");
  const params = {
    doc_id: "ZQoxvV6nTqwhrl",
    username: "huqiqi01",
    operations: [
      {
        mode: "cover",
        withNewCard: false,
        json: [card],
      },
    ],
    publish: true,
  };

  updateSummary();
  fs.writeFileSync(outputPath, `${JSON.stringify(params, null, 2)}\n`);
  process.stdout.write(
    `${JSON.stringify(
      {
        changed,
        scores,
        average: scores.reduce((sum, score) => sum + score, 0) / scores.length,
        outputPath,
        summaryPath,
      },
      null,
      2,
    )}\n`,
  );
}

process.stdin.on("end", main);
