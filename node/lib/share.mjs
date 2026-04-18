// share — manage public share links for documents.
// Outline 的 share 是"为某篇文档生成公开可访问的链接"，不同于协作者邀请。
import { apiPost, extractId } from "./api.mjs";
import { renderResponse, printJson } from "./utils.mjs";

function summShare(s) {
  if (!s || typeof s !== "object") return s;
  return {
    id: s.id,
    documentId: s.documentId,
    documentTitle: s.documentTitle,
    url: s.url,
    published: s.published,
    includeChildDocuments: s.includeChildDocuments,
    revokedAt: s.revokedAt,
    createdAt: s.createdAt,
  };
}

export async function handleShare(action, f) {
  switch (action) {
    case "list": {
      const p = {};
      if (f.limit) p.limit = parseInt(f.limit, 10);
      if (f.offset) p.offset = parseInt(f.offset, 10);
      if (f.documentId) p.documentId = extractId(f.documentId, "doc");
      renderResponse(await apiPost("shares.list", p), summShare, f.full, f);
      return;
    }
    case "info": {
      const p = {};
      if (f.id) p.id = f.id;
      if (f.documentId) p.documentId = extractId(f.documentId, "doc");
      if (Object.keys(p).length === 0) {
        printJson({ ok: false, error: "需要 --id 或 --document-id" });
        process.exit(1);
      }
      renderResponse(await apiPost("shares.info", p), summShare, f.full, f);
      return;
    }
    case "create": {
      if (!f.documentId) { printJson({ ok: false, error: "需要 --document-id" }); process.exit(1); }
      const p = { documentId: extractId(f.documentId, "doc") };
      if (f.includeChildren) p.includeChildDocuments = true;
      if (f.published) p.published = true;
      renderResponse(await apiPost("shares.create", p), summShare, f.full, f);
      return;
    }
    case "update": {
      if (!f.id) { printJson({ ok: false, error: "需要 --id（share id）" }); process.exit(1); }
      const p = { id: f.id };
      if (f.published !== undefined) p.published = f.published === true || f.published === "true";
      if (f.includeChildren !== undefined) p.includeChildDocuments = f.includeChildren === true || f.includeChildren === "true";
      renderResponse(await apiPost("shares.update", p), summShare, f.full, f);
      return;
    }
    case "revoke": {
      if (!f.id) { printJson({ ok: false, error: "需要 --id（share id）" }); process.exit(1); }
      renderResponse(await apiPost("shares.revoke", { id: f.id }), null, true);
      return;
    }
    default:
      printJson({ ok: false, error: `未知 share 动作：${action}（可用：list, info, create, update, revoke）` });
      process.exit(2);
  }
}
