export function topLevelSummary(content) {
  const nodes = Array.isArray(content) ? content : [];
  return {
    nodes: nodes.length,
    types: nodes.map((node) => node.type),
    cards: nodes.filter((node) => node.type === "card").length,
    titles: nodes.filter((node) => node.type === "title").length,
  };
}

export function isCleanDocument(content) {
  const summary = topLevelSummary(content);
  return summary.cards === 1 && summary.titles === 1;
}

export function canonicalizeDocument(content) {
  const nodes = Array.isArray(content) ? content : [];
  const cards = nodes.filter((node) => node.type === "card");
  const titles = nodes.filter((node) => node.type === "title");

  if (cards.length !== 1) {
    throw new Error(
      `无法安全规范化文档：card 数量为 ${cards.length}，不是 1。`,
    );
  }
  if (titles.length === 1) {
    return [titles[0], cards[0]];
  }
  if (
    titles.length === 2 &&
    titles[0].blockId &&
    titles[0].blockId === titles[1].blockId
  ) {
    return [titles[0], cards[0]];
  }
  throw new Error(
    `无法安全规范化文档：title 结构为 ${JSON.stringify(
      titles.map((title) => ({
        blockId: title.blockId,
        diffId: title.diffId,
      })),
    )}`,
  );
}

export function selectVerifiedBaseVersion(
  versionRecords,
  blockedVersionIds,
  contentByVersion,
) {
  for (const record of versionRecords) {
    const versionId = record?.versionId;
    if (versionId == null || blockedVersionIds.has(versionId)) continue;
    const content = contentByVersion.get(versionId);
    if (content && isCleanDocument(content)) {
      return { versionId, content };
    }
  }
  return null;
}

export function assertPublishSuccess(response) {
  const payload = response?.result ?? response;
  if (!payload?.success) {
    throw new Error(`如流编辑接口返回 success=false：${JSON.stringify(payload)}`);
  }
  if (!Array.isArray(payload.operations) || payload.operations.length === 0) {
    throw new Error(
      `如流编辑接口没有返回 operations：${JSON.stringify(payload)}`,
    );
  }
  const failedIndex = payload.operations.findIndex(
    (operation) => operation?.success !== true,
  );
  if (failedIndex !== -1) {
    throw new Error(
      `如流编辑接口返回 operations[${failedIndex}].success=false：${JSON.stringify(
        payload,
      )}`,
    );
  }
}
