#!/usr/bin/env node

import fs from "node:fs";

const outputPath = process.argv[2];
if (!outputPath) {
  throw new Error("Usage: normalize_hy3_agent_reviews_ku.mjs <output-path>");
}

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

const reviews = [
  "核心任务基本完成。",
  "主体完成，但收尾或工具调用不够稳定。",
  "部分完成，关键步骤或交付仍不完整。",
  "主体完成，但收尾或工具调用不够稳定。",
  "关键任务未完成。",
  "核心任务基本完成。",
  "关键任务未完成。",
  "部分完成，关键步骤或交付仍不完整。",
];

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
  for (let i = 0; i < reviews.length; i += 1) {
    const row = updatedTable.children[categoryIndex + i + 1];
    const cell = row.children?.[11];
    const reviewParagraph = cell?.children?.find(
      (child) =>
        child.type === "paragraph" &&
        (textOf(child).includes("独立快速补测") ||
          textOf(child).includes("当前汇报展示总分")),
    );
    if (!reviewParagraph) {
      throw new Error(`Hy3 review paragraph not found for T${String(i + 1).padStart(2, "0")}`);
    }
    reviewParagraph.children = [{ text: reviews[i] }];
    changed.push(`T${String(i + 1).padStart(2, "0")}`);
  }

  const params = {
    doc_id: "ZQoxvV6nTqwhrl",
    username: "huqiqi01",
    operations: [
      {
        mode: "cover",
        withNewCard: false,
        json: [updated[1]],
      },
    ],
    publish: true,
  };

  fs.writeFileSync(outputPath, `${JSON.stringify(params, null, 2)}\n`);
  process.stdout.write(
    `${JSON.stringify({ changed, outputPath }, null, 2)}\n`,
  );
}

process.stdin.on("end", main);
