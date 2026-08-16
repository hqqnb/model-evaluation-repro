import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { execFileSync } from "node:child_process";

const docId = "ZQoxvV6nTqwhrl";
const username = "huqiqi01";
const sourceTable =
  process.env.AGENT_SUMMARY_PATH ||
  "evaluation/agent/model_review_summary_20260815.md";
const protocol1Path = "/tmp/agent_doc_before.json";
const backupDir = process.env.AGENT_BACKUP_DIR || "/tmp/ku-agent-results";
const paramsPath = "/tmp/ku_agent_results_params.json";
const cli = "/opt/homebrew/bin/infoflow-cli";

function nodeText(node) {
  if (!node || typeof node !== "object") return "";
  if (typeof node.text === "string") return node.text;
  return Object.values(node).map(nodeText).join("");
}

function findAll(node, predicate, output = []) {
  if (!node || typeof node !== "object") return output;
  if (predicate(node)) output.push(node);
  for (const value of Object.values(node)) {
    findAll(value, predicate, output);
  }
  return output;
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function randomDiffId() {
  return Math.random().toString(36).slice(2, 10);
}

function makeParagraph(children) {
  return {
    blockId: `docyg-${randomUUID()}`,
    children,
    diffId: randomDiffId(),
    type: "paragraph",
  };
}

function makeLink(label, url) {
  return {
    children: [{ text: label }],
    href: url,
    id: `docyg-${randomUUID()}`,
    title: label,
    type: "link",
  };
}

function makeCellChildren(value) {
  return value.split("<br/>").map((part) => {
    const match = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (match) {
      return makeParagraph([
        { text: "" },
        makeLink(match[1], match[2]),
        { text: "" },
      ]);
    }
    return makeParagraph([{ text: part }]);
  });
}

function runJson(args) {
  const output = execFileSync(cli, args, {
    encoding: "utf8",
    maxBuffer: 32 * 1024 * 1024,
  });
  const parsed = JSON.parse(output);
  if (parsed.success !== true) {
    throw new Error(`infoflow-cli failed: ${output.slice(0, 2000)}`);
  }
  return parsed;
}

function readSourceCells() {
  const rows = {};
  const lines = fs.readFileSync(sourceTable, "utf8").split(/\r?\n/);
  for (const line of lines) {
    if (!line.startsWith("|")) continue;
    const parts = line.split("|");
    if (parts.length !== 16) continue;
    const rowNo = parts[1].trim();
    if (!/^[1-8]$/.test(rowNo)) continue;
    const cells = parts.slice(5, 15).map((cell) => cell.trim());
    for (const [index, cell] of cells.entries()) {
      if (!/^评分：\d+(?:\.\d+)?分/.test(cell)) {
        throw new Error(`T0${rowNo} model cell ${index + 1} has no score`);
      }
      if (!cell.includes("[完整交互预览](")) {
        throw new Error(`T0${rowNo} model cell ${index + 1} has no preview`);
      }
      if (cell.includes("未测（尚未运行）")) {
        throw new Error(`T0${rowNo} model cell ${index + 1} is untested`);
      }
    }
    rows[Number(rowNo)] = cells;
  }
  if (Object.keys(rows).length !== 8) {
    throw new Error("source table must contain T01-T08");
  }
  return rows;
}

function getBodyContent(content) {
  const card = content.find((node) => node.type === "card");
  const cardItem = card?.children?.find((node) => node.type === "card-item");
  if (!cardItem || !Array.isArray(cardItem.children)) {
    throw new Error("document card body not found");
  }
  return cardItem.children;
}

function findSummaryTable(bodyContent) {
  const tables = findAll(bodyContent, (node) => node.type === "table");
  const table = tables.find((candidate) =>
    nodeText(candidate.children?.[0]).includes("测评总结"),
  );
  if (!table) throw new Error("summary table not found");
  return table;
}

function locateAgentRows(table) {
  const rows = {};
  for (const [index, row] of table.children.entries()) {
    const cells = row.children || [];
    const rowNo = nodeText(cells[0]).trim();
    const task = nodeText(cells[1]);
    if (/^[1-8]$/.test(rowNo) && task.includes(`T0${rowNo}`)) {
      rows[Number(rowNo)] = { index, row };
    }
  }
  if (Object.keys(rows).length !== 8) {
    throw new Error("online table does not contain T01-T08");
  }
  return rows;
}

function verifyContent(content, sourceCells) {
  const body = getBodyContent(content);
  const table = findSummaryTable(body);
  const rows = locateAgentRows(table);
  for (const [rowNo, cells] of Object.entries(sourceCells)) {
    const row = rows[Number(rowNo)].row;
    for (let modelIndex = 0; modelIndex < 10; modelIndex += 1) {
      const actual = nodeText(row.children[4 + modelIndex]);
      const expectedScore = cells[modelIndex].split("<br/>")[0];
      if (
        !actual.includes(expectedScore) ||
        actual.includes("未测（尚未运行）") ||
        !actual.includes("完整交互预览")
      ) {
        throw new Error(
          `readback failed: T0${rowNo} model ${modelIndex + 1}`,
        );
      }
    }
  }
}

fs.mkdirSync(backupDir, { recursive: true });
const sourceCells = readSourceCells();
const beforeResponse = JSON.parse(fs.readFileSync(protocol1Path, "utf8"));
const beforeContent = beforeResponse.data?.result?.content;
if (!Array.isArray(beforeContent)) {
  throw new Error("protocol-1 content is missing");
}

const updatedContent = clone(beforeContent);
const table = findSummaryTable(getBodyContent(updatedContent));
const targetRows = locateAgentRows(table);
for (const [rowNo, cells] of Object.entries(sourceCells)) {
  const row = targetRows[Number(rowNo)].row;
  for (let modelIndex = 0; modelIndex < 10; modelIndex += 1) {
    const cellIndex = 4 + modelIndex;
    row.children[cellIndex] = {
      ...row.children[cellIndex],
      children: makeCellChildren(cells[modelIndex]),
    };
  }
}

const params = {
  doc_id: docId,
  username,
  operations: [
    {
      mode: "cover",
      withNewCard: false,
      // KU keeps the existing title. Cover only the body card so the title
      // is not duplicated by the editor endpoint.
      json: [updatedContent.find((node) => node.type === "card")],
    },
  ],
  publish: true,
};

fs.writeFileSync(
  path.join(backupDir, "browser-recovery-before.json"),
  `${JSON.stringify(beforeResponse, null, 2)}\n`,
);
fs.writeFileSync(paramsPath, `${JSON.stringify(params)}\n`);

const publish = runJson([
  "ku",
  "doc",
  "call",
  "editor_ku_page",
  "--params-file",
  paramsPath,
]);
const publishResult =
  publish.data?.result ?? publish.result ?? publish.data ?? publish;
if (
  publishResult.success === false ||
  publishResult.operations?.some((operation) => operation.success === false)
) {
  throw new Error(`publish returned failure: ${JSON.stringify(publish)}`);
}

const afterResponse = runJson([
  "ku",
  "doc",
  "content",
  "--doc-id",
  docId,
  "--protocol",
  "1",
]);
const afterContent = afterResponse.data?.result?.content;
if (!Array.isArray(afterContent)) throw new Error("readback content is missing");
verifyContent(afterContent, sourceCells);

const afterMarkdown = runJson([
  "ku",
  "doc",
  "content",
  "--doc-id",
  docId,
  "--protocol",
  "2",
]);
fs.writeFileSync(
  path.join(backupDir, "browser-recovery-after.md.json"),
  `${JSON.stringify(afterMarkdown, null, 2)}\n`,
);

process.stdout.write(
  JSON.stringify(
    {
      success: true,
      changedCells: 80,
      paramsPath,
      verification: "protocol-1 readback passed for all 80 model cells",
    },
    null,
    2,
  ) + "\n",
);
