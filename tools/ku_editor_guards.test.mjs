import test from "node:test";
import assert from "node:assert/strict";

import {
  assertPublishSuccess,
  canonicalizeDocument,
  isCleanDocument,
  selectVerifiedBaseVersion,
} from "./ku_editor_guards.mjs";

const cleanDocument = [
  { type: "title" },
  { type: "card", children: [{ type: "card-item", children: [] }] },
];

const duplicateTitleDocument = [
  { type: "title", blockId: "title-1" },
  { type: "title", blockId: "title-1" },
  { type: "card", children: [{ type: "card-item", children: [] }] },
];

test("duplicate-title documents are never treated as clean baselines", () => {
  assert.equal(isCleanDocument(cleanDocument), true);
  assert.equal(isCleanDocument(duplicateTitleDocument), false);
});

test("a repairable duplicate title is removed without replacing current node ids", () => {
  const canonical = canonicalizeDocument(duplicateTitleDocument);
  assert.deepEqual(
    canonical.map((node) => node.type),
    ["title", "card"],
  );
  assert.equal(canonical[0], duplicateTitleDocument[0]);
  assert.equal(canonical[1], duplicateTitleDocument[2]);
});

test("base selection only returns a verified clean version", () => {
  const result = selectVerifiedBaseVersion(
    [
      { versionId: 188 },
      { versionId: 187 },
      { versionId: 186 },
    ],
    new Set([187, 188]),
    new Map([
      [187, cleanDocument],
      [186, cleanDocument],
    ]),
  );

  assert.equal(result.versionId, 186);
});

test("a publish response with an inner failed operation is rejected", () => {
  assert.throws(
    () =>
      assertPublishSuccess({
        result: {
          success: true,
          operations: [{ success: false }],
        },
      }),
    /operations\[0\]\.success/,
  );
});
