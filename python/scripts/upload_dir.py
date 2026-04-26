import os
import sys
import json
import time
import re
import fnmatch
from .api import api_post, extract_id, require_danger_confirmation
from .attachment import upload_image_for_document


# 默认忽略：隐藏文件、版本控制、依赖目录、系统垃圾、模板自身
DEFAULT_IGNORES = [
    ".*",
    "__pycache__",
    "node_modules",
    ".git",
    ".svn",
    ".DS_Store",
    "Thumbs.db",
]

# 被识别为"目录索引"的 markdown 文件名（小写比较）
INDEX_FILENAMES = {"readme.md", "_index.md", "index.md"}


def _should_ignore(name, patterns):
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def _strip_frontmatter(text):
    """支持 --- title: xxx --- 的 YAML frontmatter，返回 (title_or_none, body_text)。"""
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    block = text[3:end]
    body = text[end + 4:].lstrip("\n")
    title = None
    for line in block.splitlines():
        line = line.strip()
        if line.lower().startswith("title:"):
            title = line.split(":", 1)[1].strip().strip("\"'")
            break
    return title, body


def process_markdown_images(text, document_id, base_dir):
    """识别 markdown / HTML 图片中的本地路径，上传后替换为 Outline 链接。"""
    import urllib.parse

    md_pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
    html_pattern = r'(<img[^>]+src=["\'])([^"\']+)(["\'][^>]*>)'

    def upload_and_get_url(image_url):
        parts = image_url.split(maxsplit=1)
        clean_url = urllib.parse.unquote(parts[0])
        if (
            not clean_url.startswith("http")
            and not clean_url.startswith("/api/attachments")
            and not clean_url.startswith("data:")
        ):
            local_path = clean_url if os.path.isabs(clean_url) else os.path.normpath(os.path.join(base_dir, clean_url))
            if os.path.exists(local_path):
                new_url = upload_image_for_document(local_path, document_id)
                if new_url:
                    return f"{new_url} {parts[1]}" if len(parts) > 1 else new_url
        return None

    def replace_md(m):
        new_url = upload_and_get_url(m.group(2).strip())
        return f"![{m.group(1)}]({new_url})" if new_url else m.group(0)

    def replace_html(m):
        new_url = upload_and_get_url(m.group(2).strip())
        return f"{m.group(1)}{new_url}{m.group(3)}" if new_url else m.group(0)

    text = re.sub(md_pattern, replace_md, text)
    text = re.sub(html_pattern, replace_html, text)
    return text


def handle_upload_dir(args):
    target_dir = args.dir
    collection_id = extract_id(args.collection_id, "collection")
    rate_limit_delay = args.delay
    dry_run = args.dry_run
    if not dry_run:
        require_danger_confirmation(
            "upload_dir 非 dry-run 批量上传",
            getattr(args, "confirm", False) or getattr(args, "confirm_dangerous", False),
        )

    if not os.path.isdir(target_dir):
        print(json.dumps({"ok": False, "error": f"Directory not found: {target_dir}"}, ensure_ascii=False))
        sys.exit(1)

    ignore_patterns = list(DEFAULT_IGNORES)
    if args.ignore:
        ignore_patterns.extend(args.ignore)

    actions = []  # for dry-run output / final summary

    def create_doc(title, text, parent_id=None):
        if dry_run:
            return {"ok": True, "data": {"id": f"<dry:{title}>"}}
        payload = {
            "collectionId": collection_id,
            "title": title,
            "text": text,
            "publish": True,
        }
        if parent_id and not parent_id.startswith("<dry:"):
            payload["parentDocumentId"] = parent_id
        res = api_post("documents.create", payload)
        time.sleep(rate_limit_delay)
        return res

    def update_doc(doc_id, title, text):
        if dry_run or doc_id.startswith("<dry:"):
            return {"ok": True}
        payload = {"id": doc_id, "title": title, "text": text}
        res = api_post("documents.update", payload)
        time.sleep(rate_limit_delay)
        return res

    def process_directory(current_dir, parent_doc_id=None):
        entries = sorted(os.listdir(current_dir))

        # 先识别目录索引文件（README.md / _index.md / index.md）
        index_file = None
        other_md_files = []
        subdirs = []
        for entry in entries:
            if _should_ignore(entry, ignore_patterns):
                continue
            full = os.path.join(current_dir, entry)
            if os.path.isdir(full):
                subdirs.append(entry)
            elif os.path.isfile(full) and entry.lower().endswith(".md"):
                if entry.lower() in INDEX_FILENAMES and index_file is None:
                    index_file = entry
                else:
                    other_md_files.append(entry)

        # 处理子目录：每个子目录创建一个父文档
        for sub in subdirs:
            full = os.path.join(current_dir, sub)
            # 子目录是否带索引文件？
            sub_index_path = None
            for cand in INDEX_FILENAMES:
                p = os.path.join(full, cand)
                if os.path.exists(p):
                    sub_index_path = p
                    break

            if sub_index_path:
                with open(sub_index_path, "r", encoding="utf-8") as f:
                    raw = f.read()
                fm_title, body = _strip_frontmatter(raw)
                folder_title = fm_title or sub
                folder_text = body
            else:
                folder_title = sub
                folder_text = f"# {folder_title}\n\n本目录索引页。"

            res = create_doc(folder_title, folder_text, parent_doc_id)
            if res.get("ok"):
                folder_doc_id = res["data"]["id"]
                actions.append({"type": "folder", "title": folder_title, "id": folder_doc_id, "status": "ok"})
                print(f"[folder] {folder_title}  → {folder_doc_id}")
                # 处理索引文件中的图片
                if sub_index_path and not dry_run:
                    new_text = process_markdown_images(folder_text, folder_doc_id, full)
                    if new_text != folder_text:
                        update_doc(folder_doc_id, folder_title, new_text)
                process_directory(full, folder_doc_id)
            else:
                actions.append({"type": "folder", "title": folder_title, "status": "fail", "error": res})
                print(f"[folder FAIL] {folder_title}: {res}")

        # 处理本目录的非索引 md 文件
        for entry in other_md_files:
            full = os.path.join(current_dir, entry)
            with open(full, "r", encoding="utf-8") as f:
                content = f.read()
            fm_title, body = _strip_frontmatter(content)
            title = fm_title or os.path.splitext(entry)[0]

            res = create_doc(title, body, parent_doc_id)
            if res.get("ok"):
                doc_id = res["data"]["id"]
                actions.append({"type": "document", "title": title, "id": doc_id, "status": "ok"})
                print(f"[doc] {title}  → {doc_id}")
                if not dry_run:
                    new_text = process_markdown_images(body, doc_id, current_dir)
                    if new_text != body:
                        update_doc(doc_id, title, new_text)
            else:
                actions.append({"type": "document", "title": title, "status": "fail", "error": res})
                print(f"[doc FAIL] {title}: {res}")

    print(f"{'[DRY RUN] ' if dry_run else ''}Uploading {target_dir} → collection {collection_id}")
    process_directory(target_dir)

    summary = {
        "ok": True,
        "dry_run": dry_run,
        "total": len(actions),
        "ok_count": sum(1 for a in actions if a.get("status") == "ok"),
        "fail_count": sum(1 for a in actions if a.get("status") == "fail"),
    }
    print("\n" + json.dumps(summary, indent=2, ensure_ascii=False))


def setup_upload_dir_parser(subparsers):
    p = subparsers.add_parser(
        "upload_dir",
        help="递归上传 markdown 目录到集合（保留层级；自动上传本地图片；支持 README/_index 作为目录索引）",
    )
    p.add_argument("--dir", required=True, help="本地目录路径")
    p.add_argument("--collection-id", required=True, help="目标集合 ID 或 URL")
    p.add_argument("--delay", type=float, default=1.0, help="每次 API 调用间隔秒（默认 1.0，遇 429 调大）")
    p.add_argument("--dry-run", action="store_true", help="只打印将要执行的操作，不写入 Outline")
    p.add_argument("--confirm", action="store_true", help="危险操作保护开启时，确认执行非 dry-run 批量上传")
    p.add_argument("--confirm-dangerous", action="store_true", help="同 --confirm；语义更明确，供脚本使用")
    p.add_argument("--ignore", action="append", help="额外忽略 glob 模式（可多次指定）")
    p.set_defaults(func=handle_upload_dir)
