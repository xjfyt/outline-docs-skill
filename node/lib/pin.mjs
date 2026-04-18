// pin — pin documents to a collection or workspace home.
import { apiPost, extractId } from "./api.mjs";
import { renderResponse, printJson } from "./utils.mjs";

function summPin(p) {
  if (!p || typeof p !== "object") return p;
  return {
    id: p.id,
    documentId: p.documentId,
    collectionId: p.collectionId,
    index: p.index,
    createdAt: p.createdAt,
  };
}

export async function handlePin(action, f) {
  switch (action) {
    case "list": {
      const p = {};
      if (f.collectionId) p.collectionId = extractId(f.collectionId, "collection");
      if (f.limit) p.limit = parseInt(f.limit, 10);
      renderResponse(await apiPost("pins.list", p), summPin, f.full, f);
      return;
    }
    case "create": {
      if (!f.documentId) { printJson({ ok: false, error: "需要 --document-id" }); process.exit(1); }
      const p = { documentId: extractId(f.documentId, "doc") };
      if (f.collectionId) p.collectionId = extractId(f.collectionId, "collection");
      if (f.index !== undefined) p.index = parseInt(f.index, 10);
      renderResponse(await apiPost("pins.create", p), summPin, f.full, f);
      return;
    }
    case "delete": {
      if (!f.id) { printJson({ ok: false, error: "需要 --id（pin id）" }); process.exit(1); }
      renderResponse(await apiPost("pins.delete", { id: f.id }), null, true);
      return;
    }
    default:
      printJson({ ok: false, error: `未知 pin 动作：${action}（可用：list, create, delete）` });
      process.exit(2);
  }
}
