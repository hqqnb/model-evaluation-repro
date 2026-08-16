#!/usr/bin/env node

import fs from "node:fs";

const outputPath = process.argv[2];
if (!outputPath) {
  throw new Error("Usage: build_agent_ku_link_update.mjs <output-path>");
}

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  input += chunk;
});

const GITHUB_BASE =
  "https://github.com/hqqnb/llm-evaluation-question-bank/blob/main/" +
  "runs/20260814-agent/responses";

const modelAliases = [
  "deepseek-v4-pro",
  "qwen3.8-max",
  "kimi-k3",
  "deepseek-v4-flash",
  "glm-5.2-internal",
  "gpt-5.6-sol",
  "opus-5",
  "hy3",
  "gpt-5.5",
  "opus-4.8",
];

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

function findLink(node) {
  if (!node || typeof node !== "object") return null;
  if (
    node.type === "link" &&
    (node.title === "完整交互预览" ||
      node.title === "完整交互回答" ||
      textOf(node) === "完整交互预览" ||
      textOf(node) === "完整交互回答")
  ) {
    return node;
  }
  for (const value of Object.values(node)) {
    const found = findLink(value);
    if (found) return found;
  }
  return null;
}

function main() {
  const current = JSON.parse(input);
  const content = current?.data?.result?.content;
  if (!Array.isArray(content)) {
    throw new Error("The query-content response has no editable content.");
  }

  const tables = findAll(content, (node) => node.type === "table");
  const table = tables.find((candidate) =>
    textOf(candidate.children?.[0]).includes("测评总结"),
  );
  if (!table) throw new Error("测评总结 table not found.");
  if (table.children.length !== 32) {
    throw new Error(`Unexpected table row count: ${table.children.length}`);
  }

  const categoryIndex = table.children.findIndex((row) =>
    textOf(row.children?.[0]).includes("类别三：Agent能力"),
  );
  if (categoryIndex < 0) throw new Error("Agent category row not found.");
  if (categoryIndex + 8 >= table.children.length) {
    throw new Error("Agent task rows are incomplete.");
  }

  const updated = structuredClone(content);
  const updatedTables = findAll(updated, (node) => node.type === "table");
  const updatedTable = updatedTables.find((candidate) =>
    textOf(candidate.children?.[0]).includes("测评总结"),
  );

  const changed = [];
  for (let taskOffset = 1; taskOffset <= 8; taskOffset += 1) {
    const row = updatedTable.children[categoryIndex + taskOffset];
    const taskNumber = textOf(row.children?.[0]).trim();
    if (taskNumber !== String(taskOffset)) {
      throw new Error(
        `Unexpected Agent row at offset ${taskOffset}: ${taskNumber}`,
      );
    }

    for (let modelOffset = 0; modelOffset < modelAliases.length; modelOffset += 1) {
      const cellIndex = 4 + modelOffset;
      const cell = row.children?.[cellIndex];
      const link = findLink(cell);
      if (!link) {
        throw new Error(
          `Preview link not found in T${String(taskOffset).padStart(2, "0")} ` +
            `${modelAliases[modelOffset]}`,
        );
      }
      const url =
        `${GITHUB_BASE}/agent-t${String(taskOffset).padStart(2, "0")}/` +
        `${modelAliases[modelOffset]}.md`;
      if (link.href !== url) {
        link.href = url;
        link.title = "完整交互预览";
        changed.push({
          task_id: `T${String(taskOffset).padStart(2, "0")}`,
          model: modelAliases[modelOffset],
          url,
        });
      }
    }
  }

  if (changed.length !== 80) {
    throw new Error(`Expected 80 link changes, got ${changed.length}`);
  }

  const params = {
    doc_id: "ZQoxvV6nTqwhrl",
    username: "huqiqi01",
    operations: [
      {
        mode: "cover",
        withNewCard: false,
        json: [updated[2]],
      },
    ],
    publish: true,
  };

  fs.writeFileSync(outputPath, `${JSON.stringify(params, null, 2)}\n`);
  process.stdout.write(
    `${JSON.stringify({ changed: changed.length, outputPath }, null, 2)}\n`,
  );
}

process.stdin.on("end", main);
