// comment — read/write comments on documents.
import { apiPost, extractId } from "./api.mjs";
import { renderResponse, printJson } from "./utils.mjs";

function summComment(c, previewLen = 200) {
  if (!c || typeof c !== "object") return c;
  let text = typeof c.data === "string" ? c.data : (c.text || "");
  if (typeof text === "string" && previewLen && text.length > previewLen) {
    text = text.slice(0, previewLen) + "…";
  }
  const createdBy = c.createdBy || {};
  return {
    id: c.id,
    documentId: c.documentId,
    parentCommentId: c.parentCommentId,
    createdBy: { id: createdBy.id, name: createdBy.name },
    createdAt: c.createdAt,
    updatedAt: c.updatedAt,
    text,
  };
}

function wrapProseMirror(text) {
  return {
    type: "doc",
    content: [{ type: "paragraph", content: [{ type: "text", text }] }],
  };
}

export async function handleComment(action, f) {
  switch (action) {
    case "list": {
      if (!f.documentId) { printJson({ ok: false, error: "需要 --document-id" }); process.exit(1); }
      const p = { documentId: extractId(f.documentId, "doc") };
      if (f.limit) p.limit = parseInt(f.limit, 10);
      if (f.offset) p.offset = parseInt(f.offset, 10);
      renderResponse(await apiPost("comments.list", p), summComment, f.full, f, 200);
      return;
    }
    case "info": {
      if (!f.id) { printJson({ ok: false, error: "需要 --id" }); process.exit(1); }
      renderResponse(await apiPost("comments.info", { id: f.id }), summComment, f.full, f, 200);
      return;
    }
    case "create": {
      if (!f.documentId || !f.text) { printJson({ ok: false, error: "需要 --document-id 与 --text" }); process.exit(1); }
      const p = { documentId: extractId(f.documentId, "doc"), data: wrapProseMirror(f.text) };
      if (f.parentCommentId) p.parentCommentId = f.parentCommentId;
      renderResponse(await apiPost("comments.create", p), summComment, f.full, f, 200);
      return;
    }
    case "update": {
      if (!f.id || !f.text) { printJson({ ok: false, error: "需要 --id 与 --text" }); process.exit(1); }
      const p = { id: f.id, data: wrapProseMirror(f.text) };
      renderResponse(await apiPost("comments.update", p), summComment, f.full, f, 200);
      return;
    }
    case "delete": {
      if (!f.id) { printJson({ ok: false, error: "需要 --id" }); process.exit(1); }
      renderResponse(await apiPost("comments.delete", { id: f.id }), null, true);
      return;
    }
    default:
      printJson({ ok: false, error: `未知 comment 动作：${action}（可用：list, info, create, update, delete）` });
      process.exit(2);
  }
}
