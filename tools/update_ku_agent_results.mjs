import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { createRequire } from "node:module";

import {
  assertPublishSuccess,
  canonicalizeDocument,
  isCleanDocument,
  topLevelSummary,
} from "./ku_editor_guards.mjs";

const require = createRequire(import.meta.url);
const { createKuService } = require(
  "/opt/homebrew/lib/node_modules/@baidu/infoflow-cli/lib/services/ku/service.js",
);

const docId = "ZQoxvV6nTqwhrl";
const username = "huqiqi01";
const sourceTable =
  process.env.AGENT_SUMMARY_PATH ||
  "evaluation/agent/model_review_summary_20260815.md";
const backupDir = process.env.AGENT_BACKUP_DIR || "/tmp/ku-agent-results";
const registryPath = path.join(backupDir, "baseline-registry.json");

const INITIAL_REGISTRY = {
  verified: [
    {
      versionId: 186,
      reason: "历史上结构正常、可作为本次 Agent 表格覆盖的安全基线",
    },
  ],
  blocked: [
    { versionId: 187, reason: "历史发布链路中的异常版本，未登记为可复用基线" },
    { versionId: 188, reason: "顶层出现重复 title 的异常版本" },
  ],
};

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

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

function findSummaryTable(content) {
  const tables = findAll(content, (node) => node.type === "table");
  const table = tables.find((candidate) =>
    nodeText(candidate.children?.[0]).includes("测评总结"),
  );
  if (!table) throw new Error("没有找到“测评总结”表格。");
  return table;
}

function tableTexts(table) {
  return table.children.map((row) =>
    row.children.map((cell) => nodeText(cell)),
  );
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

function readAgentCells() {
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
        throw new Error(`T0${rowNo} 第 ${index + 1} 个模型单元格缺少有效评分。`);
      }
      if (!cell.includes("[完整交互预览](")) {
        throw new Error(`T0${rowNo} 第 ${index + 1} 个模型单元格缺少预览链接。`);
      }
      if (cell.includes("未测（尚未运行）")) {
        throw new Error(`T0${rowNo} 第 ${index + 1} 个模型单元格仍是未测占位符。`);
      }
    }
    rows[Number(rowNo)] = cells;
  }

  if (Object.keys(rows).length !== 8) {
    throw new Error(
      `本地表格需要包含 T01-T08 8 行，实际找到 ${Object.keys(rows).length} 行。`,
    );
  }
  return rows;
}

function readRegistry() {
  if (!fs.existsSync(registryPath)) return clone(INITIAL_REGISTRY);
  const parsed = JSON.parse(fs.readFileSync(registryPath, "utf8"));
  return {
    verified: Array.isArray(parsed.verified) ? parsed.verified : [],
    blocked: Array.isArray(parsed.blocked) ? parsed.blocked : [],
  };
}

function writeRegistry(registry) {
  fs.writeFileSync(registryPath, `${JSON.stringify(registry, null, 2)}\n`);
}

function addVerifiedVersion(registry, versionId, reason) {
  const verified = registry.verified.filter(
    (entry) => Number(entry.versionId) !== Number(versionId),
  );
  verified.unshift({ versionId, reason });
  registry.verified = verified.slice(0, 20);
  writeRegistry(registry);
}

function addBlockedVersion(registry, versionId, reason) {
  if (versionId == null) return;
  const blocked = registry.blocked.filter(
    (entry) => Number(entry.versionId) !== Number(versionId),
  );
  blocked.unshift({ versionId, reason });
  registry.blocked = blocked.slice(0, 50);
  registry.verified = registry.verified.filter(
    (entry) => Number(entry.versionId) !== Number(versionId),
  );
  writeRegistry(registry);
}

function validateCleanDocument(content, phase) {
  const summary = topLevelSummary(content);
  if (!isCleanDocument(content)) {
    throw new Error(`${phase} 顶层结构异常：${JSON.stringify(summary)}`);
  }
}

function getBodyContent(content) {
  const card = content.find((node) => node.type === "card");
  const cardItem = card?.children?.find((node) => node.type === "card-item");
  if (!cardItem || !Array.isArray(cardItem.children)) {
    throw new Error("没有找到现有卡片中的正文节点。");
  }
  return cardItem.children;
}

function validateTableShape(table, phase) {
  if (!Array.isArray(table.children) || table.children.length !== 32) {
    throw new Error(
      `${phase} 表格行数异常：${table.children?.length ?? "unknown"}`,
    );
  }
  const invalidRow = table.children.findIndex(
    (row) => !Array.isArray(row.children) || row.children.length !== 14,
  );
  if (invalidRow !== -1) {
    throw new Error(`${phase} 第 ${invalidRow} 行不是 14 列。`);
  }
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
    throw new Error(
      `线上表格需要包含 T01-T08 8 行，实际找到 ${Object.keys(rows).length} 行。`,
    );
  }
  return rows;
}

function assertOnlyTargetCellsChanged(before, after, targetRows) {
  if (before.length !== after.length) {
    throw new Error(`表格行数发生变化：${before.length} -> ${after.length}`);
  }
  let changed = 0;
  for (let rowIndex = 0; rowIndex < before.length; rowIndex += 1) {
    if (before[rowIndex].length !== after[rowIndex].length) {
      throw new Error(`第 ${rowIndex} 行列数发生变化。`);
    }
    for (let cellIndex = 0; cellIndex < before[rowIndex].length; cellIndex += 1) {
      if (before[rowIndex][cellIndex] === after[rowIndex][cellIndex]) continue;
      const isAgentRow = targetRows.has(rowIndex);
      const isTargetCell = cellIndex >= 4 && cellIndex <= 13;
      if (!isAgentRow || !isTargetCell) {
        throw new Error(
          `发现非目标单元格被修改：row=${rowIndex}, cell=${cellIndex}`,
        );
      }
      changed += 1;
    }
  }
  if (changed !== 80) {
    throw new Error(`预期修改 80 个模型单元格，实际修改 ${changed} 个。`);
  }
}

function writeFailure(details) {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  fs.writeFileSync(
    path.join(backupDir, `failure-${stamp}.json`),
    `${JSON.stringify(details, null, 2)}\n`,
  );
}

const service = createKuService({ format: "json", dryRun: false });

async function request(endpoint, data, operation) {
  return service.request({ endpoint, data, operation, service: "doc" });
}

async function queryVersions() {
  return request(
    "/ku/openapi/queryVersion",
    { docId, pageNum: 1, pageSize: 1000 },
    "query Agent table document versions",
  );
}

async function queryContent(versionId) {
  return request(
    "/ku/openapi/queryContent",
    { docId, showDocInfo: true, protocol: 1, versionId },
    `query Agent table document version ${versionId}`,
  );
}

fs.mkdirSync(backupDir, { recursive: true });

const registry = readRegistry();
writeRegistry(registry);
const sourceCells = readAgentCells();
const versionsBefore = await queryVersions();
const versionRecords = versionsBefore.result?.data || [];
const latestBefore = versionRecords[0]?.versionId;
if (!latestBefore) throw new Error("没有读取到当前文档版本。");

const latestResponse = await queryContent(latestBefore);
const latestContent = latestResponse.result?.content;
let beforeContent;
try {
  // Keep the current version's blockId/diffId values. Older versions may
  // look identical but contain stale editor node versions and are rejected.
  beforeContent = canonicalizeDocument(latestContent);
} catch (error) {
  throw new Error(`当前版本无法安全修复，已停止写入：${error.message}`);
}

const baseVersion = latestBefore;
const beforeBodyContent = getBodyContent(beforeContent);
const beforeTable = findSummaryTable(beforeBodyContent);
validateTableShape(beforeTable, "写入前");
const beforeRows = locateAgentRows(beforeTable);
const beforeTexts = tableTexts(beforeTable);

const updatedContent = clone(beforeContent);
const updatedBodyContent = getBodyContent(updatedContent);
const updatedTable = findSummaryTable(updatedBodyContent);
const updatedRows = locateAgentRows(updatedTable);

for (const [rowNo, cells] of Object.entries(sourceCells)) {
  const row = updatedRows[Number(rowNo)].row;
  for (let cellIndex = 4; cellIndex < 14; cellIndex += 1) {
    row.children[cellIndex] = {
      ...row.children[cellIndex],
      children: makeCellChildren(cells[cellIndex - 4]),
    };
  }
}

const operationPayload = {
  doc_id: docId,
  username,
  observedLatestVersion: latestBefore,
  baseVersion,
  publish: true,
  operations: [
    {
      mode: "cover",
      // Use the proven recovery shape: replace the complete clean
      // title/card document instead of asking KU to wrap a complex body.
      withNewCard: false,
      json: updatedContent,
    },
  ],
};

fs.writeFileSync(
  path.join(backupDir, `before-${baseVersion}.json`),
  `${JSON.stringify(
    {
      observedLatestVersion: latestBefore,
      baseVersion,
      response: { result: { content: beforeContent } },
    },
    null,
    2,
  )}\n`,
);
fs.writeFileSync(
  path.join(backupDir, `operations-${baseVersion}.json`),
  `${JSON.stringify(operationPayload, null, 2)}\n`,
);

const versionsImmediatelyBeforeWrite = await queryVersions();
const latestImmediatelyBeforeWrite =
  versionsImmediatelyBeforeWrite.result?.data?.[0]?.versionId;
if (latestImmediatelyBeforeWrite !== latestBefore) {
  throw new Error(
    `写入前版本发生变化：${latestBefore} -> ${latestImmediatelyBeforeWrite}，已中止。`,
  );
}

let editResult;
try {
  editResult = await request(
    "/ku/openapi/editContent",
    {
      docGuid: docId,
      editorUsername: username,
      operations: operationPayload.operations,
      publish: true,
    },
    "update Agent model scores and preview links",
  );
  assertPublishSuccess(editResult);
} catch (error) {
  writeFailure({
    phase: "publish",
    error: error.message,
    response: editResult ?? null,
    operationPayload,
  });
  throw error;
}

const versionsAfter = await queryVersions();
const updatedVersion = versionsAfter.result?.data?.[0]?.versionId;
if (!updatedVersion || Number(updatedVersion) === Number(latestBefore)) {
  throw new Error("编辑接口没有生成新版本。");
}

let afterResponse;
try {
  afterResponse = await queryContent(updatedVersion);
  const afterContent = afterResponse.result?.content;
  validateCleanDocument(afterContent, "写入后");
  const afterBodyContent = getBodyContent(afterContent);
  const afterTable = findSummaryTable(afterBodyContent);
  validateTableShape(afterTable, "写入后");
  const afterRows = locateAgentRows(afterTable);
  const afterTexts = tableTexts(afterTable);
  assertOnlyTargetCellsChanged(
    beforeTexts,
    afterTexts,
    new Set(Object.values(beforeRows).map(({ index }) => index)),
  );

  for (const [rowNo, cells] of Object.entries(sourceCells)) {
    const row = afterRows[Number(rowNo)].row;
    for (let cellIndex = 4; cellIndex < 14; cellIndex += 1) {
      const expectedScore = cells[cellIndex - 4].split("<br/>")[0];
      const actualText = nodeText(row.children[cellIndex]);
      if (
        !actualText.includes(expectedScore) ||
        actualText.includes("未测（尚未运行）") ||
        !actualText.includes("完整交互预览")
      ) {
        throw new Error(
          `写入后校验失败：T0${rowNo} 第 ${cellIndex + 1} 列内容不完整。`,
        );
      }
    }
  }

  fs.writeFileSync(
    path.join(backupDir, `after-${updatedVersion}.json`),
    `${JSON.stringify(afterResponse, null, 2)}\n`,
  );
  addVerifiedVersion(
    registry,
    Number(updatedVersion),
    "本脚本发布后通过顶层、表格、80 个目标单元格和非目标单元格校验",
  );

  process.stdout.write(
    `${JSON.stringify(
      {
        success: true,
        observedLatestVersion: latestBefore,
        baseVersion,
        updatedVersion,
        changedCells: 80,
        beforeTopLevel: topLevelSummary(beforeContent),
        afterTopLevel: topLevelSummary(afterContent),
        backupDir,
        registryPath,
      },
      null,
      2,
    )}\n`,
  );
} catch (error) {
  writeFailure({
    phase: "post_publish_verification",
    error: error.message,
    updatedVersion,
    baseVersion,
    response: afterResponse ?? null,
  });
  addBlockedVersion(registry, Number(updatedVersion), error.message);
  throw error;
}
