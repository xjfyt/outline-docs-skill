"""template 子命令 —— 列出 / 查看 / 校验 markdown 文档模板。

模板存放规则：
- 内置模板目录：<skill_root>/templates/
- 自定义模板目录：环境变量 OUTLINE_TEMPLATES_DIR（同名时优先于内置）
- 每个模板 = 一个 .md（正文）+ 同名 .meta.json（元数据）
"""
import os
import re
import sys
import json
import glob
from .utils import print_json


def _builtin_templates_dir():
    # python/scripts/template.py → ../../templates
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, "..", "..", "templates"))


def _all_template_dirs():
    dirs = [_builtin_templates_dir()]
    custom = os.environ.get("OUTLINE_TEMPLATES_DIR")
    if custom and os.path.isdir(custom):
        dirs.insert(0, custom)  # 自定义优先
    return dirs


def _load_template(name):
    """返回 (md_path, md_content, meta_dict_or_None)。找不到时返回 (None, None, None)。"""
    for d in _all_template_dirs():
        if not os.path.isdir(d):
            continue
        for root, dirs, files in os.walk(d):
            if f"{name}.md" in files:
                md = os.path.join(root, f"{name}.md")
                with open(md, "r", encoding="utf-8") as f:
                    content = f.read()
                meta_path = os.path.join(root, f"{name}.meta.json")
                meta = None
                if os.path.exists(meta_path):
                    with open(meta_path, "r", encoding="utf-8") as f:
                        try:
                            meta = json.load(f)
                        except json.JSONDecodeError as e:
                            meta = {"_meta_parse_error": str(e)}
                return md, content, meta
    return None, None, None


def _list_templates():
    seen = {}
    for d in _all_template_dirs():
        if not os.path.isdir(d):
            continue
        for root, dirs, files in os.walk(d):
            for file in sorted(files):
                if file.endswith(".md"):
                    name = file[:-3]
                    if name.lower() == "readme":
                        continue
                    if name in seen:
                        continue
                    meta_path = os.path.join(root, f"{name}.meta.json")
                    desc = ""
                    if os.path.exists(meta_path):
                        try:
                            with open(meta_path, "r", encoding="utf-8") as f:
                                meta = json.load(f)
                            desc = meta.get("description", "")
                        except Exception:
                            pass
                    category = os.path.relpath(root, d)
                    if category == ".":
                        category = ""
                    else:
                        category = category.replace("\\", "/")
                    seen[name] = {"name": name, "category": category, "description": desc, "source": root}
    return list(seen.values())


# ---- lint ------------------------------------------------------------------
_H1_RE = re.compile(r"^# (?!#)")
_H2_RE = re.compile(r"^## (?!#)")
_H3_RE = re.compile(r"^### (?!#)")
_H1_SECTION_NUMBERED_RE = re.compile(r"^# [一二三四五六七八九十]+、")
_H2_BOLD_NUMBERED_RE = re.compile(r"^## \*\*\d+、.+\*\*$")
_H3_CHINESE_PAREN_RE = re.compile(r"^### （\d+）")


def _lint(content, meta):
    issues = []
    lines = content.split("\n")

    # 1. 必须出现的 section
    section_titles = []
    for line in lines:
        if line.startswith("# "):
            stripped = line[2:].strip()
            stripped = re.sub(r"^[一二三四五六七八九十]+、", "", stripped).strip()
            section_titles.append(stripped)

    required = (meta or {}).get("required_sections") or []
    for s in required:
        if not any(s in t for t in section_titles):
            issues.append({"type": "missing_required_section", "section": s})

    # 2. 标题层级编号风格
    rules = (meta or {}).get("lint_rules") or {}
    for i, line in enumerate(lines):
        if rules.get("section_must_use_h1") and _H1_RE.match(line):
            stripped = line[2:].strip()
            # 跳过文档主标题（第一个 H1，可能不带中文数字）
            if i > 0 and not _H1_SECTION_NUMBERED_RE.match(line):
                # 主标题模板 # N、xxx 也可接受（数字+顿号）
                if not re.match(r"^# \d+、", line):
                    issues.append({"type": "h1_numbering", "line": i + 1, "text": line})
        if rules.get("subsection_must_use_h2_bold_arabic") and _H2_RE.match(line):
            if not _H2_BOLD_NUMBERED_RE.match(line.strip()):
                # 容忍 "## 1、xxx" 但提示
                issues.append({"type": "h2_style_should_be_bold_arabic", "line": i + 1, "text": line.strip()})
        if rules.get("sub_subsection_must_use_h3_chinese_paren") and _H3_RE.match(line):
            if not _H3_CHINESE_PAREN_RE.match(line):
                issues.append({"type": "h3_should_use_chinese_paren_numbering", "line": i + 1, "text": line.strip()})

    # 3. 标题块之间应有空行
    if rules.get("blank_line_between_blocks"):
        for i in range(1, len(lines)):
            if (lines[i].startswith("# ") or lines[i].startswith("## ") or lines[i].startswith("### ")):
                if lines[i - 1].strip() != "":
                    issues.append({"type": "missing_blank_line_before_heading", "line": i + 1, "text": lines[i]})

    return issues


# ---- handler ---------------------------------------------------------------
def handle_template(args):
    if args.action == "list":
        items = _list_templates()
        print_json({"ok": True, "count": len(items), "items": items, "search_dirs": _all_template_dirs()})

    elif args.action == "show":
        if not args.name:
            available = [t["name"] for t in _list_templates()]
            print_json({"ok": False, "error": "需要 --name", "available": available}); sys.exit(1)
        md_path, content, meta = _load_template(args.name)
        if content is None:
            available = [t["name"] for t in _list_templates()]
            print_json({"ok": False, "error": f"未找到模板：{args.name}", "available": available}); sys.exit(1)
        if args.body_only:
            print(content)
            return
        print_json({
            "ok": True,
            "name": args.name,
            "path": md_path,
            "meta": meta,
            "body": content,
        })

    elif args.action == "lint":
        if not args.name:
            available = [t["name"] for t in _list_templates()]
            print_json({"ok": False, "error": "需要 --name 指定要对照的模板", "available": available}); sys.exit(1)
        if not args.file or not os.path.exists(args.file):
            print_json({"ok": False, "error": f"找不到文件：{args.file}"}); sys.exit(1)
        _, _, meta = _load_template(args.name)
        if meta is None:
            available = [t["name"] for t in _list_templates()]
            print_json({"ok": False, "error": f"模板 {args.name} 缺少 meta.json", "available": available}); sys.exit(1)
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read()
        issues = _lint(content, meta)
        print_json({
            "ok": len(issues) == 0,
            "file": args.file,
            "template": args.name,
            "issue_count": len(issues),
            "issues": issues,
        })


def setup_template_parser(subparsers):
    p = subparsers.add_parser("template", help="文档模板：列出 / 查看 / 校验")
    p.add_argument("action", choices=["list", "show", "lint"])
    p.add_argument("--name", help="模板名（如 api-endpoint）")
    p.add_argument("--body-only", action="store_true", help="show：只输出模板正文（不含 meta，节省 token）")
    p.add_argument("--file", help="lint：要校验的本地 markdown 文件路径")
    p.set_defaults(func=handle_template)
