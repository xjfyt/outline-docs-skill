"""pin subcommand — pin documents to a collection or workspace home."""
import sys
from .api import api_post, extract_id
from .utils import render_response, print_json


def _summ_pin(p, preview_len=None):
    if not isinstance(p, dict):
        return p
    return {
        "id": p.get("id"),
        "documentId": p.get("documentId"),
        "collectionId": p.get("collectionId"),
        "index": p.get("index"),
        "createdAt": p.get("createdAt"),
    }


def handle_pin(args):
    if args.action == "list":
        payload = {}
        if args.collection_id: payload["collectionId"] = extract_id(args.collection_id, "collection")
        if getattr(args, "limit", None): payload["limit"] = args.limit
        res = api_post("pins.list", payload)
        render_response(res, summarizer=_summ_pin, full=args.full)

    elif args.action == "create":
        if not args.document_id:
            print_json({"ok": False, "error": "需要 --document-id"}); sys.exit(1)
        payload = {"documentId": extract_id(args.document_id, "doc")}
        if args.collection_id: payload["collectionId"] = extract_id(args.collection_id, "collection")
        if args.index is not None: payload["index"] = int(args.index)
        res = api_post("pins.create", payload)
        render_response(res, summarizer=_summ_pin, full=args.full)

    elif args.action == "delete":
        if not args.id:
            print_json({"ok": False, "error": "需要 --id（pin id）"}); sys.exit(1)
        res = api_post("pins.delete", {"id": args.id})
        render_response(res, full=True)


def setup_pin_parser(subparsers):
    p = subparsers.add_parser("pin", help="置顶文档到集合 / 工作区主页")
    p.add_argument("action", choices=["list", "create", "delete"])
    p.add_argument("--id", help="pin ID（delete 用）")
    p.add_argument("--document-id", help="create：要置顶的文档")
    p.add_argument("--collection-id", help="list/create：集合级置顶（留空为工作区主页）")
    p.add_argument("--index", type=int, help="create：置顶位置")
    p.add_argument("--limit", type=int)
    p.add_argument("--full", action="store_true")
    p.set_defaults(func=handle_pin)
