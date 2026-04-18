import fs from "node:fs";
import path from "node:path";
import { apiPost, extractId } from "./api.mjs";
import { printJson } from "./utils.mjs";

function guessMime(filepath) {
  const ext = path.extname(filepath).toLowerCase();
  const map = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
    ".bmp": "image/bmp", ".ico": "image/x-icon",
    ".pdf": "application/pdf", ".md": "text/markdown",
    ".txt": "text/plain", ".json": "application/json",
    ".zip": "application/zip", ".tar": "application/x-tar",
    ".mp4": "video/mp4", ".mp3": "audio/mpeg",
  };
  return map[ext] || "application/octet-stream";
}

async function postFile(uploadUrl, formData, filepath, timeoutMs = 60_000) {
  const buf = await fs.promises.readFile(filepath);
  const contentType = guessMime(filepath);
  const blob = new Blob([buf], { type: contentType });
  const form = new FormData();
  for (const [k, v] of Object.entries(formData)) form.append(k, String(v));
  form.append("file", blob, path.basename(filepath));
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(uploadUrl, { method: "POST", body: form, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

export async function handleUpload(_action, f) {
  if (!f.filepath) { printJson({ ok: false, error: "需要 --filepath" }); process.exit(1); }
  if (!f.documentId) { printJson({ ok: false, error: "需要 --document-id" }); process.exit(1); }
  const filepath = f.filepath;
  const documentId = extractId(f.documentId, "doc");
  if (!fs.existsSync(filepath)) {
    printJson({ ok: false, error: `File not found: ${filepath}` });
    process.exit(1);
  }
  const stat = await fs.promises.stat(filepath);
  const name = path.basename(filepath);
  const payload = { name, size: stat.size, contentType: guessMime(filepath), documentId };
  const res = await apiPost("attachments.create", payload);
  if (!res.ok) { printJson(res); process.exit(1); }
  const { uploadUrl, form, attachment } = res.data;
  const uploadRes = await postFile(uploadUrl, form, filepath);
  if (uploadRes.status === 200 || uploadRes.status === 204) {
    printJson({
      ok: true,
      attachment_url: attachment.url,
      markdown: `![${name}](${attachment.url})`,
    });
  } else {
    printJson({ ok: false, status: uploadRes.status, error: await uploadRes.text() });
  }
}

export async function uploadImageForDocument(filepath, documentId, maxRetries = 3) {
  if (!fs.existsSync(filepath)) return null;
  const stat = await fs.promises.stat(filepath);
  const name = path.basename(filepath);
  const payload = { name, size: stat.size, contentType: guessMime(filepath), documentId };
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const res = await apiPost("attachments.create", payload);
      if (!res.ok) {
        console.log(`Failed to get upload URL for ${filepath}: ${JSON.stringify(res)}`);
        return null;
      }
      const { uploadUrl, form, attachment } = res.data;
      const uploadRes = await postFile(uploadUrl, form, filepath);
      if (uploadRes.status === 200 || uploadRes.status === 204) return attachment.url;
      console.log(`Failed to upload ${filepath}: ${uploadRes.status}`);
      return null;
    } catch (e) {
      if (attempt < maxRetries - 1) {
        console.log(`Connection error uploading ${filepath}, retrying (${attempt + 1}/${maxRetries})...`);
        await new Promise((r) => setTimeout(r, 2000));
      } else {
        console.log(`Failed to upload ${filepath} after ${maxRetries} attempts: ${e.message || e}`);
        return null;
      }
    }
  }
  return null;
}
