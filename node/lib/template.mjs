import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { printJson } from "./utils.mjs";

function builtinTemplatesDir() {
  const here = path.dirname(fileURLToPath(import.meta.url));
  return path.normalize(path.join(here, "..", "..", "templates"));
}

function allTemplateDirs() {
  const dirs = [builtinTemplatesDir()];
  const custom = process.env.OUTLINE_TEMPLATES_DIR;
  if (custom && fs.existsSync(custom) && fs.statSync(custom).isDirectory()) dirs.unshift(custom);
  return dirs;
}

function loadTemplate(name) {
  for (const d of allTemplateDirs()) {
    const md = path.join(d, `${name}.md`);
    if (!fs.existsSync(md)) continue;
    const content = fs.readFileSync(md, "utf8");
    const metaPath = path.join(d, `${name}.meta.json`);
    let meta = null;
    if (fs.existsSync(metaPath)) {
      try { meta = JSON.parse(fs.readFileSync(metaPath, "utf8")); }
      catch (e) { meta = { _meta_parse_error: String(e.message || e) }; }
    }
    return { mdPath: md, content, meta };
  }
  return { mdPath: null, content: null, meta: null };
}

function listTemplates() {
  const seen = new Map();
  for (const d of allTemplateDirs()) {
    if (!fs.existsSync(d)) continue;
    const files = fs.readdirSync(d).filter((f) => f.endsWith(".md")).sort();
    for (const file of files) {
      const name = path.basename(file, ".md");
      if (name.toLowerCase() === "readme") continue;
      if (seen.has(name)) continue;
      const metaPath = path.join(d, `${name}.meta.json`);
      let description = "";
      if (fs.existsSync(metaPath)) {
        try { description = JSON.parse(fs.readFileSync(metaPath, "utf8")).description || ""; }
        catch {}
      }
      seen.set(name, { name, description, source: d });
    }
  }
  return [...seen.values()];
}

const H1_RE = /^# (?!#)/;
const H2_RE = /^## (?!#)/;
const H3_RE = /^### (?!#)/;
const H1_SECTION_NUMBERED_RE = /^# [一二三四五六七八九十]+、/;
const H1_ARABIC_NUMBERED_RE = /^# \d+、/;
const H2_BOLD_NUMBERED_RE = /^## \*\*\d+、.+\*\*$/;
const H3_CHINESE_PAREN_RE = /^### （\d+）/;

function lintContent(content, meta) {
  const issues = [];
  const lines = content.split("\n");
  const sectionTitles = [];
  for (const line of lines) {
    if (line.startsWith("# ")) {
      let stripped = line.slice(2).trim();
      stripped = stripped.replace(/^[一二三四五六七八九十]+、/, "").trim();
      sectionTitles.push(stripped);
    }
  }
  const required = (meta && meta.required_sections) || [];
  for (const s of required) {
    if (!sectionTitles.some((t) => t.includes(s))) {
      issues.push({ type: "missing_required_section", section: s });
    }
  }
  const rules = (meta && meta.lint_rules) || {};
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (rules.section_must_use_h1 && H1_RE.test(line)) {
      if (i > 0 && !H1_SECTION_NUMBERED_RE.test(line) && !H1_ARABIC_NUMBERED_RE.test(line)) {
        issues.push({ type: "h1_numbering", line: i + 1, text: line });
      }
    }
    if (rules.subsection_must_use_h2_bold_arabic && H2_RE.test(line)) {
      if (!H2_BOLD_NUMBERED_RE.test(line.trim())) {
        issues.push({ type: "h2_style_should_be_bold_arabic", line: i + 1, text: line.trim() });
      }
    }
    if (rules.sub_subsection_must_use_h3_chinese_paren && H3_RE.test(line)) {
      if (!H3_CHINESE_PAREN_RE.test(line)) {
        issues.push({ type: "h3_should_use_chinese_paren_numbering", line: i + 1, text: line.trim() });
      }
    }
  }
  if (rules.blank_line_between_blocks) {
    for (let i = 1; i < lines.length; i++) {
      const l = lines[i];
      if (l.startsWith("# ") || l.startsWith("## ") || l.startsWith("### ")) {
        if (lines[i - 1].trim() !== "") {
          issues.push({ type: "missing_blank_line_before_heading", line: i + 1, text: l });
        }
      }
    }
  }
  return issues;
}

export async function handleTemplate(action, f) {
  if (action === "list") {
    const items = listTemplates();
    printJson({ ok: true, count: items.length, items, search_dirs: allTemplateDirs() });
    return;
  }
  if (action === "show") {
    if (!f.name) {
      const available = listTemplates().map((t) => t.name);
      printJson({ ok: false, error: "需要 --name", available }); process.exit(1);
    }
    const { mdPath, content, meta } = loadTemplate(f.name);
    if (content === null) {
      const available = listTemplates().map((t) => t.name);
      printJson({ ok: false, error: `未找到模板：${f.name}`, available }); process.exit(1);
    }
    if (f.bodyOnly) { console.log(content); return; }
    printJson({ ok: true, name: f.name, path: mdPath, meta, body: content });
    return;
  }
  if (action === "lint") {
    if (!f.name) {
      const available = listTemplates().map((t) => t.name);
      printJson({ ok: false, error: "需要 --name 指定要对照的模板", available }); process.exit(1);
    }
    if (!f.file || !fs.existsSync(f.file)) { printJson({ ok: false, error: `找不到文件：${f.file}` }); process.exit(1); }
    const { meta } = loadTemplate(f.name);
    if (!meta) {
      const available = listTemplates().map((t) => t.name);
      printJson({ ok: false, error: `模板 ${f.name} 缺少 meta.json`, available }); process.exit(1);
    }
    const content = fs.readFileSync(f.file, "utf8");
    const issues = lintContent(content, meta);
    printJson({ ok: issues.length === 0, file: f.file, template: f.name, issue_count: issues.length, issues });
    return;
  }
  printJson({ ok: false, error: `未知 template 动作：${action}（可用：list, show, lint）` });
  process.exit(2);
}
