#!/usr/bin/env node

import fs from "node:fs";

const outputPath = process.argv[2];
if (!outputPath) {
  throw new Error("Usage: update_coding_c06_score_ku.mjs <output-path>");
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

function main() {
  const current = JSON.parse(input);
  const content = current?.data?.result?.content;
  if (!Array.isArray(content)) {
    throw new Error("The query-content response has no editable content.");
  }

  const table = findAll(content, (node) => node.type === "table")[0];
  if (!table) throw new Error("Main evaluation table not found.");
  const rowIndex = table.children.findIndex((row) =>
    textOf(row.children?.[1]).includes("弓箭射击模拟游戏"),
  );
  if (rowIndex < 0) throw new Error("coding-c06 row not found.");

  const updated = structuredClone(content);
  const updatedTable = findAll(updated, (node) => node.type === "table")[0];
  const cell = updatedTable.children[rowIndex].children?.[11];
  if (!cell) throw new Error("Hunyuan 3 cell not found.");
  const previewParagraph = cell.children.find(
    (child) => child.type === "paragraph" && textOf(child).includes("预览"),
  );
  if (!previewParagraph) throw new Error("Existing preview link not found.");

  const review =
    "评分：7分依据：核心玩法完整，四个靶子、蓄力射击、计时和排行榜均可正常使用，但画面和交互较为简单，整体完成度一般";
  previewParagraph.children[0] = {
    ...(previewParagraph.children[0] ?? {}),
    text: `${review}；`,
  };

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
    `${JSON.stringify({ rowIndex, score: 7, review, outputPath }, null, 2)}\n`,
  );
}

process.stdin.on("end", main);
