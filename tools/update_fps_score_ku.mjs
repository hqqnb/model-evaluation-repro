#!/usr/bin/env node

import fs from "node:fs";

const outputPath = process.argv[2];
if (!outputPath) {
  throw new Error("Usage: update_fps_score_ku.mjs <output-path>");
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

  const table = findAll(content, (node) => node.type === "table").find(
    (candidate) =>
      textOf(candidate.children?.[0]).includes("序号") &&
      textOf(candidate.children?.[0]).includes("hy3"),
  );
  if (!table) throw new Error("Main evaluation table not found.");

  const rowIndex = table.children.findIndex((row) => {
    const rowText = textOf(row);
    return (
      rowText.includes("Counter-Strike") ||
      rowText.includes("FPS") ||
      rowText.includes("Dust2")
    );
  });
  if (rowIndex < 0) throw new Error("FPS task row not found.");

  const updated = structuredClone(content);
  const updatedTable = findAll(updated, (node) => node.type === "table").find(
    (candidate) =>
      textOf(candidate.children?.[0]).includes("序号") &&
      textOf(candidate.children?.[0]).includes("hy3"),
  );
  const cell = updatedTable.children[rowIndex].children[11];
  if (!cell) throw new Error("Hunyuan 3 cell not found.");

  const reviewText =
    "评分：5分；依据：页面可以打开并显示场景，但存在严重 Bug，无法正常进入对局，整体不具备可玩性";
  const previewParagraph = cell.children.find(
    (child) => child.type === "paragraph" && textOf(child).includes("预览"),
  );
  if (!previewParagraph) {
    throw new Error("Existing FPS preview link was not found.");
  }
  const previewIndex = cell.children.indexOf(previewParagraph);
  const alreadyScored = cell.children.find(
    (child) => child.type === "paragraph" && textOf(child).includes("评分：5分"),
  );
  if (!alreadyScored) {
    previewParagraph.children[0] = {
      ...(previewParagraph.children[0] ?? {}),
      text: `${reviewText}；`,
    };
  } else {
    alreadyScored.children = [{ text: reviewText }];
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
    `${JSON.stringify(
      {
        rowIndex,
        score: 5,
        review: reviewText,
        outputPath,
      },
      null,
      2,
    )}\n`,
  );
}

process.stdin.on("end", main);
