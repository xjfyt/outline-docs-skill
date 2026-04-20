import os
import sys
from .api import api_post, extract_id, paginate_all
from .utils import render_response, summarize_doc, print_json, _resolve_preview_len


def _read_text_arg(args):
    """Allow --text or --text-file (avoids huge CLI args / shell escaping)."""
    tf = getattr(args, "text_file", None)
    if tf:
        if not os.path.exists(tf):
            print_json({"ok": False, "error": f"--text-file 不存在：{tf}"})
            sys.exit(1)
        with open(tf, "r", encoding="utf-8") as f:
            return f.read()
    return args.text


def handle_document(args):
    if args.action == "list":
        payload = {}
        if args.collection_id:
            payload["collectionId"] = extract_id(args.collection_id, "collection")
        if getattr(args, "parent_document_id", None):
            payload["parentDocumentId"] = extract_id(args.parent_document_id, "doc")
        if getattr(args, "limit", None):
            payload["limit"] = args.limit
        if getattr(args, "offset", None):
            payload["offset"] = args.offset
        if getattr(args, "sort", None):
            payload["sort"] = args.sort
        if getattr(args, "direction", None):
            payload["direction"] = args.direction
        if getattr(args, "all", False):
            res = paginate_all("documents.list", payload)
        else:
            res = api_post("documents.list", payload)
        render_response(res, summarizer=summarize_doc, full=args.full, args=args)

    elif args.action == "view":
        doc_id = extract_id(args.id, "doc")
        res = api_post("documents.info", {"id": doc_id})
        if args.text_only:
            if isinstance(res, dict) and res.get("ok") is False:
                print_json(res)
                sys.exit(1)
            data = res.get("data", {}) if isinstance(res, dict) else {}
            print(data.get("text", ""))
        else:
            render_response(res, summarizer=summarize_doc, full=args.full, args=args)

    elif args.action == "create":
        text = _read_text_arg(args) or ""
        payload = {
            "title": args.title,
            "text": text,
            "publish": not args.draft,
        }
        if args.collection_id:
            payload["collectionId"] = extract_id(args.collection_id, "collection")
        if args.parent_document_id:
            payload["parentDocumentId"] = extract_id(args.parent_document_id, "doc")
        if args.icon:
            payload["icon"] = args.icon
        if args.template_id:
            payload["templateId"] = extract_id(args.template_id, "doc")
        res = api_post("documents.create", payload)
        render_response(res, summarizer=summarize_doc, full=args.full, args=args)
        if getattr(args, "clean_file", False) and getattr(args, "text_file", None):
            if isinstance(res, dict) and res.get("ok", True) is not False:
                try: os.remove(args.text_file)
                except Exception: pass

    elif args.action == "update":
        doc_id = extract_id(args.id, "doc")
        payload = {"id": doc_id}
        mode = getattr(args, "mode", "replace") or "replace"

        if mode == "replace":
            if args.title:
                payload["title"] = args.title
            text = _read_text_arg(args)
            if text is not None:
                payload["text"] = text
        elif mode == "append":
            text = _read_text_arg(args)
            if text is None:
                print_json({"ok": False, "error": "append 模式需要 --text 或 --text-file"})
                sys.exit(1)
            payload["text"] = text
            payload["append"] = True
        elif mode == "patch":
            if not args.find:
                print_json({"ok": False, "error": "patch 模式需要 --find 与 --replace（或 --text/--text-file）"})
                sys.exit(1)
            replacement = args.replace if args.replace is not None else _read_text_arg(args)
            if replacement is None:
                print_json({"ok": False, "error": "patch 模式缺少替换内容（--replace / --text / --text-file）"})
                sys.exit(1)
            payload["editMode"] = "patch"
            payload["findText"] = args.find
            payload["text"] = replacement

        if args.publish:
            payload["publish"] = True
        if args.done:
            payload["done"] = True

        res = api_post("documents.update", payload)
        render_response(res, summarizer=summarize_doc, full=args.full, args=args)
        if getattr(args, "clean_file", False) and getattr(args, "text_file", None):
            if isinstance(res, dict) and res.get("ok", True) is not False:
                try: os.remove(args.text_file)
                except Exception: pass

    elif args.action == "delete":
        doc_id = extract_id(args.id, "doc")
        payload = {"id": doc_id}
        if args.permanent:
            payload["permanent"] = True
        res = api_post("documents.delete", payload)
        render_response(res, full=True)

    elif args.action == "move":
        doc_id = extract_id(args.id, "doc")
        payload = {"id": doc_id}
        if args.collection_id:
            payload["collectionId"] = extract_id(args.collection_id, "collection")
        if args.parent_document_id:
            payload["parentDocumentId"] = extract_id(args.parent_document_id, "doc")
        if getattr(args, "index", None) is not None:
            payload["index"] = int(args.index)
        res = api_post("documents.move", payload)
        render_response(res, full=args.full)

    elif args.action == "search":
        payload = {"query": args.query}
        if args.collection_id:
            payload["collectionId"] = extract_id(args.collection_id, "collection")
        if getattr(args, "limit", None):
            payload["limit"] = args.limit
        if getattr(args, "status_filter", None):
            payload["statusFilter"] = args.status_filter.split(",")
        endpoint = "documents.searchTitles" if args.titles_only else "documents.search"
        res = paginate_all(endpoint, payload) if getattr(args, "all", False) else api_post(endpoint, payload)
        # search 返回结构：{data: [{document: {...}, ranking: ...}], ...}
        if not args.full and isinstance(res, dict) and isinstance(res.get("data"), list):
            preview_len = _resolve_preview_len(args, 120)
            items = []
            for hit in res["data"]:
                doc = hit.get("document") if isinstance(hit, dict) and "document" in hit else hit
                items.append(summarize_doc(doc, preview_len=preview_len))
            print_json({"ok": True, "count": len(items), "items": items})
        else:
            render_response(res, summarizer=summarize_doc, full=args.full, args=args)

    elif args.action == "find":
        # 按标题精确/模糊查找，返回最匹配的几条（用于"用户给标题让 AI 改文档"场景）
        payload = {"query": args.query}
        if args.collection_id:
            payload["collectionId"] = extract_id(args.collection_id, "collection")
        payload["limit"] = args.limit or 5
        res = api_post("documents.searchTitles", payload)
        if isinstance(res, dict) and res.get("ok") is False:
            print_json(res)
            sys.exit(1)
        preview_len = _resolve_preview_len(args, 120)
        items = []
        for hit in (res.get("data") or []):
            doc = hit.get("document") if isinstance(hit, dict) and "document" in hit else hit
            items.append(summarize_doc(doc, preview_len=preview_len))
        print_json({"ok": True, "count": len(items), "items": items})

    elif args.action == "archive":
        res = api_post("documents.archive", {"id": extract_id(args.id, "doc")})
        render_response(res, summarizer=summarize_doc, full=args.full, args=args)

    elif args.action == "restore":
        payload = {"id": extract_id(args.id, "doc")}
        if args.collection_id:
            payload["collectionId"] = extract_id(args.collection_id, "collection")
        res = api_post("documents.restore", payload)
        render_response(res, summarizer=summarize_doc, full=args.full, args=args)

    elif args.action == "unpublish":
        res = api_post("documents.unpublish", {"id": extract_id(args.id, "doc")})
        render_response(res, summarizer=summarize_doc, full=args.full, args=args)

    elif args.action == "duplicate":
        payload = {"id": extract_id(args.id, "doc")}
        if args.title:
            payload["title"] = args.title
        if args.collection_id:
            payload["collectionId"] = extract_id(args.collection_id, "collection")
        if args.parent_document_id:
            payload["parentDocumentId"] = extract_id(args.parent_document_id, "doc")
        res = api_post("documents.duplicate", payload)
        render_response(res, summarizer=summarize_doc, full=args.full, args=args)

    elif args.action == "export":
        # Returns {data: {...markdown text or download info...}}
        res = api_post("documents.export", {"id": extract_id(args.id, "doc")})
        if isinstance(res, dict) and res.get("ok") is False:
            print_json(res)
            sys.exit(1)
        data = res.get("data") if isinstance(res, dict) else None
        if isinstance(data, str):
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(data)
                print_json({"ok": True, "output": args.output, "bytes": len(data)})
            else:
                print(data)
        else:
            print_json(res)

    elif args.action == "drafts":
        res = api_post("documents.drafts", {"limit": args.limit or 25})
        render_response(res, summarizer=summarize_doc, full=args.full, args=args)

    elif args.action == "archived":
        res = api_post("documents.archived", {"limit": args.limit or 25})
        render_response(res, summarizer=summarize_doc, full=args.full, args=args)


def setup_document_parser(subparsers):
    p = subparsers.add_parser("document", help="文档（Document）管理")
    p.add_argument(
        "action",
        choices=[
            "list", "view", "create", "update", "delete", "move", "search",
            "find", "archive", "restore", "unpublish", "duplicate", "export",
            "drafts", "archived",
        ],
    )
    p.add_argument("--id", help="文档 ID 或 URL（自动解析）")
    p.add_argument("--collection-id", help="集合 ID 或 URL")
    p.add_argument("--title", help="文档标题")
    p.add_argument("--text", help="Markdown 内容")
    p.add_argument("--text-file", help="从文件读取 Markdown 内容（推荐用于长内容）")
    p.add_argument("--clean-file", action="store_true", help="如果存在 --text-file，执行成功后自动删除本地临时文件（供 AI 使用）")
    p.add_argument("--parent-document-id", help="父文档 ID 或 URL")
    p.add_argument("--query", help="搜索关键词（search/find）")
    p.add_argument("--titles-only", action="store_true", help="search：仅按标题搜索（更快）")
    p.add_argument("--status-filter", help="search：状态过滤，逗号分隔（draft,archived,published）")
    p.add_argument("--mode", choices=["replace", "append", "patch"], default="replace",
                   help="update 模式：replace=整篇替换；append=追加；patch=按 --find 找一段替换")
    p.add_argument("--find", help="patch 模式：要替换的原文片段")
    p.add_argument("--replace", help="patch 模式：替换为的新内容（也可用 --text/--text-file）")
    p.add_argument("--icon", help="create：图标")
    p.add_argument("--template-id", help="create：基于 Outline 服务端模板的 ID（服务端模板；与本 skill 的 `template` 子命令是两码事 —— 后者是本地 markdown 写作模板）")
    p.add_argument("--draft", action="store_true", help="create：保存为草稿（默认直接发布）")
    p.add_argument("--publish", action="store_true", help="update：将草稿发布")
    p.add_argument("--done", action="store_true", help="update：标记完成")
    p.add_argument("--permanent", action="store_true", help="delete：永久删除（不放回收站）")
    p.add_argument("--limit", type=int, help="分页大小")
    p.add_argument("--offset", type=int, help="分页起点")
    p.add_argument("--sort", help="list：排序字段（updatedAt/createdAt/title/index）")
    p.add_argument("--direction", choices=["ASC", "DESC"], help="list：排序方向")
    p.add_argument("--text-only", action="store_true", help="view：仅输出 Markdown 正文")
    p.add_argument("--output", help="export：写入文件路径（默认 stdout）")
    p.add_argument("--full", action="store_true", help="输出完整 JSON（默认摘要）")
    p.add_argument("--preview-len", type=int, help="摘要 textPreview 字数；0=不要 preview（更省 token，默认 120）")
    p.add_argument("--all", action="store_true", help="list/search/find：自动翻页累积所有结果")
    p.add_argument("--index", type=int, help="move：集合/父文档内的索引位置（0 起）")
    p.set_defaults(func=handle_document)
