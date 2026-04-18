// api — raw Outline API escape hatch.
// 用于访问本 skill 尚未封装的端点（如 stars.*, fileOperations.*, groups.* 等）。
import fs from "node:fs";
import { apiPost, paginateAll } from "./api.mjs";
import { printJson } from "./utils.mjs";

export async function handleApi(action, f) {
  if (action !== "call") {
    printJson({ ok: false, error: "仅支持 'api call'（通用 POST 端点）" });
    process.exit(2);
  }
  if (!f.endpoint) {
    printJson({
      ok: false,
      error: "需要 --endpoint <name>（如 documents.info / stars.list / fileOperations.list）",
      docs: "https://www.getoutline.com/developers",
    });
    process.exit(1);
  }

  let payload = {};
  if (f.data) {
    try { payload = JSON.parse(f.data); }
    catch (e) { printJson({ ok: false, error: `--data 不是合法 JSON：${e.message || e}` }); process.exit(1); }
    if (typeof payload !== "object" || Array.isArray(payload) || payload === null) {
      printJson({ ok: false, error: "--data 必须是 JSON 对象（{...}）" });
      process.exit(1);
    }
  }
  if (f.dataFile) {
    if (!fs.existsSync(f.dataFile)) {
      printJson({ ok: false, error: `--data-file 不存在：${f.dataFile}` });
      process.exit(1);
    }
    try { payload = JSON.parse(fs.readFileSync(f.dataFile, "utf8")); }
    catch (e) { printJson({ ok: false, error: `--data-file 不是合法 JSON：${e.message || e}` }); process.exit(1); }
  }

  const res = f.all
    ? await paginateAll(f.endpoint, payload)
    : await apiPost(f.endpoint, payload);
  printJson(res);
}
