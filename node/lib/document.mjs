import fs from "node:fs";
import { apiPost, extractId, paginateAll } from "./api.mjs";
import { renderResponse, summarizeDoc, printJson } from "./utils.mjs";

function readTextArg(f) {
  if (f.textFile) {
    if (!fs.existsSync(f.textFile)) {
      printJson({ ok: false, error: `--text-file 不存在：${f.textFile}` });
      process.exit(1);
    }
    return fs.readFileSync(f.textFile, "utf8");
  }
  return f.text;
}

function die(msg) {
  printJson({ ok: false, error: msg });
  process.exit(1);
}

function resolvePreviewLen(f, fallback = 120) {
  if (!f || f.previewLen === undefined || f.previewLen === "") return fallback;
  const n = parseInt(f.previewLen, 10);
  return Number.isFinite(n) && n >= 0 ? n : fallback;
}

export async function handleDocument(action, f) {
  switch (action) {
    case "list": {
      const p = {};
      if (f.collectionId) p.collectionId = extractId(f.collectionId, "collection");
      if (f.parentDocumentId) p.parentDocumentId = extractId(f.parentDocumentId, "doc");
      if (f.limit) p.limit = parseInt(f.limit, 10);
      if (f.offset) p.offset = parseInt(f.offset, 10);
      if (f.sort) p.sort = f.sort;
      if (f.direction) p.direction = f.direction;
      const res = f.all ? await paginateAll("documents.list", p) : await apiPost("documents.list", p);
      renderResponse(res, summarizeDoc, f.full, f);
      return;
    }
    case "view": {
      const res = await apiPost("documents.info", { id: extractId(f.id, "doc") });
      if (f.textOnly) {
        if (res && res.ok === false) { printJson(res); process.exit(1); }
        console.log((res.data || {}).text || "");
      } else {
        renderResponse(res, summarizeDoc, f.full, f);
      }
      return;
    }
    case "create": {
      const text = readTextArg(f) || "";
      const p = { title: f.title, text, publish: !f.draft };
      if (f.collectionId) p.collectionId = extractId(f.collectionId, "collection");
      if (f.parentDocumentId) p.parentDocumentId = extractId(f.parentDocumentId, "doc");
      if (f.icon) p.icon = f.icon;
      if (f.templateId) p.templateId = extractId(f.templateId, "doc");
      const res = await apiPost("documents.create", p);
      renderResponse(res, summarizeDoc, f.full, f);
      if (f.cleanFile && f.textFile && res && res.ok !== false) {
        try { fs.unlinkSync(f.textFile); } catch (e) {}
      }
      return;
    }
    case "update": {
      const p = { id: extractId(f.id, "doc") };
      const mode = f.mode || "replace";
      if (mode === "replace") {
        if (f.title) p.title = f.title;
        const t = readTextArg(f);
        if (t !== undefined) p.text = t;
      } else if (mode === "append") {
        const t = readTextArg(f);
        if (t === undefined) die("append 模式需要 --text 或 --text-file");
        p.text = t;
        p.append = true;
      } else if (mode === "patch") {
        if (!f.find) die("patch 模式需要 --find 与 --replace（或 --text/--text-file）");
        const r = f.replace !== undefined ? f.replace : readTextArg(f);
        if (r === undefined) die("patch 模式缺少替换内容（--replace / --text / --text-file）");
        p.editMode = "patch";
        p.findText = f.find;
        p.text = r;
      } else {
        die(`未知 --mode：${mode}（可选 replace|append|patch）`);
      }
      if (f.publish) p.publish = true;
      if (f.done) p.done = true;
      const res = await apiPost("documents.update", p);
      renderResponse(res, summarizeDoc, f.full, f);
      if (f.cleanFile && f.textFile && res && res.ok !== false) {
        try { fs.unlinkSync(f.textFile); } catch (e) {}
      }
      return;
    }
    case "delete": {
      const p = { id: extractId(f.id, "doc") };
      if (f.permanent) p.permanent = true;
      renderResponse(await apiPost("documents.delete", p), null, true);
      return;
    }
    case "move": {
      const p = { id: extractId(f.id, "doc") };
      if (f.collectionId) p.collectionId = extractId(f.collectionId, "collection");
      if (f.parentDocumentId) p.parentDocumentId = extractId(f.parentDocumentId, "doc");
      if (f.index !== undefined) {
        const idx = parseInt(f.index, 10);
        if (Number.isFinite(idx)) p.index = idx;
      }
      renderResponse(await apiPost("documents.move", p), null, f.full);
      return;
    }
    case "search": {
      const p = { query: f.query };
      if (f.collectionId) p.collectionId = extractId(f.collectionId, "collection");
      if (f.limit) p.limit = parseInt(f.limit, 10);
      if (f.statusFilter) p.statusFilter = String(f.statusFilter).split(",");
      const endpoint = f.titlesOnly ? "documents.searchTitles" : "documents.search";
      const res = f.all ? await paginateAll(endpoint, p) : await apiPost(endpoint, p);
      if (!f.full && res && Array.isArray(res.data)) {
        const previewLen = resolvePreviewLen(f);
        const items = res.data.map((hit) => summarizeDoc(hit?.document ?? hit, previewLen));
        printJson({ ok: true, count: items.length, items });
      } else {
        renderResponse(res, summarizeDoc, f.full, f);
      }
      return;
    }
    case "find": {
      const p = { query: f.query, limit: parseInt(f.limit || 5, 10) };
      if (f.collectionId) p.collectionId = extractId(f.collectionId, "collection");
      const res = await apiPost("documents.searchTitles", p);
      if (res && res.ok === false) { printJson(res); process.exit(1); }
      const previewLen = resolvePreviewLen(f);
      const items = (res.data || []).map((hit) => summarizeDoc(hit?.document ?? hit, previewLen));
      printJson({ ok: true, count: items.length, items });
      return;
    }
    case "archive":
      renderResponse(await apiPost("documents.archive", { id: extractId(f.id, "doc") }), summarizeDoc, f.full, f);
      return;
    case "restore": {
      const p = { id: extractId(f.id, "doc") };
      if (f.collectionId) p.collectionId = extractId(f.collectionId, "collection");
      renderResponse(await apiPost("documents.restore", p), summarizeDoc, f.full, f);
      return;
    }
    case "unpublish":
      renderResponse(await apiPost("documents.unpublish", { id: extractId(f.id, "doc") }), summarizeDoc, f.full, f);
      return;
    case "duplicate": {
      const p = { id: extractId(f.id, "doc") };
      if (f.title) p.title = f.title;
      if (f.collectionId) p.collectionId = extractId(f.collectionId, "collection");
      if (f.parentDocumentId) p.parentDocumentId = extractId(f.parentDocumentId, "doc");
      renderResponse(await apiPost("documents.duplicate", p), summarizeDoc, f.full, f);
      return;
    }
    case "export": {
      const res = await apiPost("documents.export", { id: extractId(f.id, "doc") });
      if (res && res.ok === false) { printJson(res); process.exit(1); }
      const data = res.data;
      if (typeof data === "string") {
        if (f.output) {
          fs.writeFileSync(f.output, data, "utf8");
          printJson({ ok: true, output: f.output, bytes: data.length });
        } else {
          console.log(data);
        }
      } else {
        printJson(res);
      }
      return;
    }
    case "drafts":
      renderResponse(await apiPost("documents.drafts", { limit: parseInt(f.limit || 25, 10) }), summarizeDoc, f.full, f);
      return;
    case "archived":
      renderResponse(await apiPost("documents.archived", { limit: parseInt(f.limit || 25, 10) }), summarizeDoc, f.full, f);
      return;
    default:
      die(`未知 document 动作：${action}`);
  }
}
