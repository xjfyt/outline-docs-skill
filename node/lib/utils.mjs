export function printJson(data, indent = 2) {
  console.log(JSON.stringify(data, null, indent));
}

function truncate(s, n) {
  if (typeof s !== "string" || !n || n <= 0) return s;
  return s.length <= n ? s : s.slice(0, n) + "…";
}

export function summarizeDoc(doc, previewLen = 120) {
  if (!doc || typeof doc !== "object") return doc;
  const out = {
    id: doc.id,
    title: doc.title,
    url: doc.url,
    collectionId: doc.collectionId,
    parentDocumentId: doc.parentDocumentId,
    updatedAt: doc.updatedAt,
    archivedAt: doc.archivedAt,
    publishedAt: doc.publishedAt,
  };
  if (previewLen && previewLen > 0) {
    out.textPreview = truncate(doc.text || "", previewLen);
  }
  return out;
}

export function summarizeCollection(coll, previewLen = 100) {
  if (!coll || typeof coll !== "object") return coll;
  const out = {
    id: coll.id,
    name: coll.name,
    url: coll.url,
    permission: coll.permission,
    updatedAt: coll.updatedAt,
  };
  if (previewLen && previewLen > 0) {
    out.description = truncate(coll.description || "", previewLen);
  }
  return out;
}

function resolvePreviewLen(flags, fallback) {
  if (!flags) return fallback;
  const raw = flags.previewLen;
  if (raw === undefined || raw === "") return fallback;
  const n = parseInt(raw, 10);
  return Number.isFinite(n) && n >= 0 ? n : fallback;
}

export function renderResponse(res, summarizer = null, full = false, flags = null, defaultPreview = 120) {
  if (res && res.ok === false) {
    printJson(res);
    process.exit(1);
  }
  if (full || !summarizer) {
    printJson(res);
    return;
  }
  const previewLen = resolvePreviewLen(flags, defaultPreview);
  const call = (x) => summarizer(x, previewLen);
  const data = res && typeof res === "object" ? res.data : res;
  if (Array.isArray(data)) {
    const out = { ok: true, count: data.length, items: data.map(call) };
    if (res && res.pagination) out.pagination = res.pagination;
    printJson(out);
  } else if (data && typeof data === "object") {
    printJson({ ok: true, data: call(data) });
  } else {
    printJson(res);
  }
}
