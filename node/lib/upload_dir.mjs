import fs from "node:fs";
import path from "node:path";
import { apiPost, extractId } from "./api.mjs";
import { uploadImageForDocument } from "./attachment.mjs";
import { printJson } from "./utils.mjs";

const DEFAULT_IGNORES = [
  ".*", "__pycache__", "node_modules", ".git", ".svn", ".DS_Store", "Thumbs.db",
];
const INDEX_FILENAMES = new Set(["readme.md", "_index.md", "index.md"]);

function globToRegex(glob) {
  let re = "^";
  for (const c of glob) {
    if (c === "*") re += ".*";
    else if (c === "?") re += ".";
    else if (".+^$()|[]{}\\".includes(c)) re += "\\" + c;
    else re += c;
  }
  return new RegExp(re + "$");
}

function shouldIgnore(name, patterns) {
  return patterns.some((p) => globToRegex(p).test(name));
}

function stripFrontmatter(text) {
  if (!text.startsWith("---")) return { title: null, body: text };
  const end = text.indexOf("\n---", 3);
  if (end === -1) return { title: null, body: text };
  const block = text.slice(3, end);
  const body = text.slice(end + 4).replace(/^\n+/, "");
  let title = null;
  for (const line of block.split(/\r?\n/)) {
    const t = line.trim();
    if (t.toLowerCase().startsWith("title:")) {
      title = t.slice(6).trim().replace(/^["']|["']$/g, "");
      break;
    }
  }
  return { title, body };
}

async function processMarkdownImages(text, documentId, baseDir) {
  const mdRe = /!\[([^\]]*)\]\(([^)]+)\)/g;
  const htmlRe = /(<img[^>]+src=["'])([^"']+)(["'][^>]*>)/g;

  async function resolveUrl(raw) {
    const parts = raw.trim().split(/\s+/);
    let clean;
    try { clean = decodeURIComponent(parts[0]); } catch { clean = parts[0]; }
    if (clean.startsWith("http") || clean.startsWith("/api/attachments") || clean.startsWith("data:")) return null;
    const localPath = path.isAbsolute(clean) ? clean : path.normalize(path.join(baseDir, clean));
    if (!fs.existsSync(localPath)) return null;
    const newUrl = await uploadImageForDocument(localPath, documentId);
    if (!newUrl) return null;
    return parts.length > 1 ? `${newUrl} ${parts.slice(1).join(" ")}` : newUrl;
  }

  async function replaceAll(source, re, build) {
    const matches = [];
    let m;
    re.lastIndex = 0;
    while ((m = re.exec(source)) !== null) matches.push({ m, index: m.index });
    let out = source;
    for (let i = matches.length - 1; i >= 0; i--) {
      const { m, index } = matches[i];
      const replacement = await build(m);
      if (replacement !== null) {
        out = out.slice(0, index) + replacement + out.slice(index + m[0].length);
      }
    }
    return out;
  }

  text = await replaceAll(text, mdRe, async (m) => {
    const u = await resolveUrl(m[2]);
    return u ? `![${m[1]}](${u})` : null;
  });
  text = await replaceAll(text, htmlRe, async (m) => {
    const u = await resolveUrl(m[2]);
    return u ? `${m[1]}${u}${m[3]}` : null;
  });
  return text;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function handleUploadDir(_action, f) {
  const targetDir = f.dir;
  if (!targetDir || !fs.existsSync(targetDir) || !fs.statSync(targetDir).isDirectory()) {
    printJson({ ok: false, error: `Directory not found: ${targetDir}` });
    process.exit(1);
  }
  if (!f.collectionId) { printJson({ ok: false, error: "需要 --collection-id" }); process.exit(1); }
  const collectionId = extractId(f.collectionId, "collection");
  const delay = f.delay ? parseFloat(f.delay) : 1.0;
  const dryRun = !!f.dryRun;
  const ignorePatterns = [...DEFAULT_IGNORES, ...(f.ignore || [])];
  const actions = [];

  async function createDoc(title, text, parentId) {
    if (dryRun) return { ok: true, data: { id: `<dry:${title}>` } };
    const payload = { collectionId, title, text, publish: true };
    if (parentId && !String(parentId).startsWith("<dry:")) payload.parentDocumentId = parentId;
    const res = await apiPost("documents.create", payload);
    await sleep(delay * 1000);
    return res;
  }

  async function updateDoc(id, title, text) {
    if (dryRun || String(id).startsWith("<dry:")) return { ok: true };
    const res = await apiPost("documents.update", { id, title, text });
    await sleep(delay * 1000);
    return res;
  }

  async function processDir(currentDir, parentDocId = null) {
    const entries = (await fs.promises.readdir(currentDir)).sort();
    let indexFile = null;
    const otherMd = [];
    const subdirs = [];
    for (const name of entries) {
      if (shouldIgnore(name, ignorePatterns)) continue;
      const full = path.join(currentDir, name);
      const stat = await fs.promises.stat(full);
      if (stat.isDirectory()) subdirs.push(name);
      else if (stat.isFile() && name.toLowerCase().endsWith(".md")) {
        if (INDEX_FILENAMES.has(name.toLowerCase()) && !indexFile) indexFile = name;
        else otherMd.push(name);
      }
    }

    for (const sub of subdirs) {
      const full = path.join(currentDir, sub);
      let subIndexPath = null;
      for (const cand of INDEX_FILENAMES) {
        const p = path.join(full, cand);
        if (fs.existsSync(p)) { subIndexPath = p; break; }
      }
      let folderTitle, folderText;
      if (subIndexPath) {
        const raw = await fs.promises.readFile(subIndexPath, "utf8");
        const { title, body } = stripFrontmatter(raw);
        folderTitle = title || sub;
        folderText = body;
      } else {
        folderTitle = sub;
        folderText = `# ${folderTitle}\n\n本目录索引页。`;
      }
      const res = await createDoc(folderTitle, folderText, parentDocId);
      if (res.ok) {
        const folderDocId = res.data.id;
        actions.push({ type: "folder", title: folderTitle, id: folderDocId, status: "ok" });
        console.log(`[folder] ${folderTitle}  → ${folderDocId}`);
        if (subIndexPath && !dryRun) {
          const newText = await processMarkdownImages(folderText, folderDocId, full);
          if (newText !== folderText) await updateDoc(folderDocId, folderTitle, newText);
        }
        await processDir(full, folderDocId);
      } else {
        actions.push({ type: "folder", title: folderTitle, status: "fail", error: res });
        console.log(`[folder FAIL] ${folderTitle}: ${JSON.stringify(res)}`);
      }
    }

    for (const entry of otherMd) {
      const full = path.join(currentDir, entry);
      const content = await fs.promises.readFile(full, "utf8");
      const { title: fmTitle, body } = stripFrontmatter(content);
      const title = fmTitle || path.basename(entry, path.extname(entry));
      const res = await createDoc(title, body, parentDocId);
      if (res.ok) {
        const docId = res.data.id;
        actions.push({ type: "document", title, id: docId, status: "ok" });
        console.log(`[doc] ${title}  → ${docId}`);
        if (!dryRun) {
          const newText = await processMarkdownImages(body, docId, currentDir);
          if (newText !== body) await updateDoc(docId, title, newText);
        }
      } else {
        actions.push({ type: "document", title, status: "fail", error: res });
        console.log(`[doc FAIL] ${title}: ${JSON.stringify(res)}`);
      }
    }
  }

  console.log(`${dryRun ? "[DRY RUN] " : ""}Uploading ${targetDir} → collection ${collectionId}`);
  await processDir(targetDir);
  console.log();
  printJson({
    ok: true,
    dry_run: dryRun,
    total: actions.length,
    ok_count: actions.filter((a) => a.status === "ok").length,
    fail_count: actions.filter((a) => a.status === "fail").length,
  });
}
