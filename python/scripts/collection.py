from .api import api_post, extract_id, paginate_all
from .utils import render_response, summarize_collection, summarize_doc, print_json


def _walk_tree(nodes, depth=0, lines=None):
    if lines is None:
        lines = []
    for n in nodes or []:
        title = n.get("title") or "(无标题)"
        lines.append(f"{'  ' * depth}- {title}  [{n.get('id')}]")
        children = n.get("children") or []
        if children:
            _walk_tree(children, depth + 1, lines)
    return lines


def handle_collection(args):
    if args.action == "list":
        payload = {}
        if getattr(args, "limit", None):
            payload["limit"] = args.limit
        if getattr(args, "offset", None):
            payload["offset"] = args.offset
        res = api_post("collections.list", payload)
        render_response(res, summarizer=summarize_collection, full=args.full, args=args)

    elif args.action == "view":
        cid = extract_id(args.id, "collection")
        res = api_post("collections.info", {"id": cid})
        render_response(res, summarizer=summarize_collection, full=args.full, args=args)

    elif args.action == "create":
        payload = {"name": args.name}
        if args.description:
            payload["description"] = args.description
        if args.private:
            payload["permission"] = None  # private
        else:
            payload["permission"] = "read_write"
        res = api_post("collections.create", payload)
        render_response(res, summarizer=summarize_collection, full=args.full, args=args)

    elif args.action == "update":
        cid = extract_id(args.id, "collection")
        payload = {"id": cid}
        if args.name:
            payload["name"] = args.name
        if args.description is not None:
            payload["description"] = args.description
        res = api_post("collections.update", payload)
        render_response(res, summarizer=summarize_collection, full=args.full, args=args)

    elif args.action == "delete":
        cid = extract_id(args.id, "collection")
        res = api_post("collections.delete", {"id": cid})
        render_response(res, full=True)

    elif args.action == "tree":
        cid = extract_id(args.id, "collection")
        res = api_post("collections.documents", {"id": cid})
        if isinstance(res, dict) and res.get("ok") is False:
            print_json(res)
            return
        nodes = res.get("data") if isinstance(res, dict) else res
        if args.full:
            print_json(res)
        else:
            print("\n".join(_walk_tree(nodes)))

    elif args.action == "reorder":
        cid = extract_id(args.id, "collection")
        res = api_post("collections.documents", {"id": cid})
        if isinstance(res, dict) and res.get("ok") is False:
            print_json(res)
            return

        nodes = res.get("data") if isinstance(res, dict) else res
        
        target_nodes = None
        pid = args.parent_document_id if hasattr(args, "parent_document_id") else None
        if pid:
            pid = extract_id(pid, "doc")
            queue = list(nodes)
            while queue:
                curr = queue.pop(0)
                if curr.get("id") == pid:
                    target_nodes = curr.get("children") or []
                    break
                queue.extend(curr.get("children") or [])
        else:
            target_nodes = nodes
            
        if target_nodes is None:
            print_json({"ok": False, "error": "未找到指定的 parent-document-id 或节点为空"})
            return
            
        if not target_nodes:
            print_json({"ok": True, "msg": "目录下无子文档可排序"})
            return

        sort_by = getattr(args, "sort_by", "title") or "title"
        rev = getattr(args, "direction", "ASC") == "DESC"
        # simple dict string sort
        target_nodes.sort(key=lambda x: str(x.get(sort_by, "")), reverse=rev)

        moved = []
        for idx, n in enumerate(target_nodes):
            payload = {
                "id": n["id"],
                "collectionId": cid,
                "index": idx
            }
            if pid:
                payload["parentDocumentId"] = pid
            api_post("documents.move", payload)
            moved.append(n.get("title"))
            
        print_json({"ok": True, "msg": f"成功重排 {len(moved)} 篇文档", "order": moved})

    elif args.action == "documents":
        # Flat list of all documents in a collection
        cid = extract_id(args.id, "collection")
        payload = {"collectionId": cid}
        if getattr(args, "limit", None):
            payload["limit"] = args.limit
        if getattr(args, "offset", None):
            payload["offset"] = args.offset
        if getattr(args, "all", False):
            res = paginate_all("documents.list", payload)
        else:
            res = api_post("documents.list", payload)
        render_response(res, summarizer=summarize_doc, full=args.full, args=args)


def setup_collection_parser(subparsers):
    p = subparsers.add_parser("collection", help="文档集（Collection）管理")
    p.add_argument(
        "action",
        choices=["list", "view", "create", "update", "delete", "tree", "documents", "reorder"],
        help="子操作；tree=层级结构, documents=该集合内文档, reorder=批量重排文档",
    )
    p.add_argument("--id", help="Collection ID 或 URL")
    p.add_argument("--parent-document-id", help="reorder: 若想对该文章下属子文档排序可指定此项")
    p.add_argument("--sort-by", default="title", help="reorder: 依据什么排序，默认 title")
    p.add_argument("--direction", choices=["ASC", "DESC"], default="ASC", help="reorder: 排序方向")
    p.add_argument("--name", help="集合名")
    p.add_argument("--description", help="集合描述")
    p.add_argument("--private", action="store_true", help="设为私有集合")
    p.add_argument("--limit", type=int, help="分页大小")
    p.add_argument("--offset", type=int, help="分页起点")
    p.add_argument("--full", action="store_true", help="输出完整 JSON（默认输出摘要）")
    p.add_argument("--preview-len", type=int, help="摘要中 description/textPreview 字数；0=不要 preview")
    p.add_argument("--all", action="store_true", help="documents：自动翻页累积所有结果")
    p.set_defaults(func=handle_collection)
