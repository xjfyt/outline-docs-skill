// revision — read document revision history (read-only).
import { apiPost, extractId } from "./api.mjs";
import { renderResponse, printJson } from "./utils.mjs";

function summRevision(r, previewLen = 120) {
  if (!r || typeof r !== "object") return r;
  const by = r.createdBy || {};
  const out = {
    id: r.id,
    documentId: r.documentId,
    title: r.title,
    createdBy: { id: by.id, name: by.name },
    createdAt: r.createdAt,
  };
  if (previewLen && previewLen > 0) {
    const t = r.text || "";
    out.textPreview = t.length > previewLen ? t.slice(0, previewLen) + "…" : t;
  }
  return out;
}

export async function handleRevision(action, f) {
  switch (action) {
    case "list": {
      if (!f.documentId) { printJson({ ok: false, error: "需要 --document-id" }); process.exit(1); }
      const p = { documentId: extractId(f.documentId, "doc") };
      if (f.limit) p.limit = parseInt(f.limit, 10);
      if (f.offset) p.offset = parseInt(f.offset, 10);
      renderResponse(await apiPost("revisions.list", p), summRevision, f.full, f);
      return;
    }
    case "info": {
      if (!f.id) { printJson({ ok: false, error: "需要 --id" }); process.exit(1); }
      renderResponse(await apiPost("revisions.info", { id: f.id }), summRevision, f.full, f);
      return;
    }
    default:
      printJson({ ok: false, error: `未知 revision 动作：${action}（可用：list, info）` });
      process.exit(2);
  }
}
