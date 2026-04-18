"""share subcommand — manage public share links for documents.

注意：Outline 的 share 是"为某篇文档生成公开可访问的链接"，不同于协作者邀请。
"""
import sys
from .api import api_post, extract_id
from .utils import render_response, print_json


def _summ_share(s, preview_len=None):
    if not isinstance(s, dict):
        return s
    return {
        "id": s.get("id"),
        "documentId": s.get("documentId"),
        "documentTitle": s.get("documentTitle"),
        "url": s.get("url"),
        "published": s.get("published"),
        "includeChildDocuments": s.get("includeChildDocuments"),
        "revokedAt": s.get("revokedAt"),
        "createdAt": s.get("createdAt"),
    }


def handle_share(args):
    if args.action == "list":
        payload = {}
        if getattr(args, "limit", None): payload["limit"] = args.limit
        if getattr(args, "offset", None): payload["offset"] = args.offset
        if args.document_id: payload["documentId"] = extract_id(args.document_id, "doc")
        res = api_post("shares.list", payload)
        render_response(res, summarizer=_summ_share, full=args.full)

    elif args.action == "info":
        payload = {}
        if args.id: payload["id"] = args.id
        if args.document_id: payload["documentId"] = extract_id(args.document_id, "doc")
        if not payload:
            print_json({"ok": False, "error": "需要 --id 或 --document-id"}); sys.exit(1)
        res = api_post("shares.info", payload)
        render_response(res, summarizer=_summ_share, full=args.full)

    elif args.action == "create":
        if not args.document_id:
            print_json({"ok": False, "error": "需要 --document-id"}); sys.exit(1)
        payload = {"documentId": extract_id(args.document_id, "doc")}
        if args.include_children: payload["includeChildDocuments"] = True
        if args.published: payload["published"] = True
        res = api_post("shares.create", payload)
        render_response(res, summarizer=_summ_share, full=args.full)

    elif args.action == "update":
        if not args.id:
            print_json({"ok": False, "error": "需要 --id（share id）"}); sys.exit(1)
        payload = {"id": args.id}
        if args.published is not None: payload["published"] = args.published
        if args.include_children is not None: payload["includeChildDocuments"] = args.include_children
        res = api_post("shares.update", payload)
        render_response(res, summarizer=_summ_share, full=args.full)

    elif args.action == "revoke":
        if not args.id:
            print_json({"ok": False, "error": "需要 --id（share id）"}); sys.exit(1)
        res = api_post("shares.revoke", {"id": args.id})
        render_response(res, full=True)


def setup_share_parser(subparsers):
    p = subparsers.add_parser("share", help="管理文档公开分享链接")
    p.add_argument("action", choices=["list", "info", "create", "update", "revoke"])
    p.add_argument("--id", help="share ID（update/revoke 用）")
    p.add_argument("--document-id", help="文档 ID 或 URL")
    p.add_argument("--published", action="store_true", help="create/update：公开发布（可匿名访问）")
    p.add_argument("--include-children", action="store_true", help="create/update：是否包含子文档")
    p.add_argument("--limit", type=int)
    p.add_argument("--offset", type=int)
    p.add_argument("--full", action="store_true")
    p.set_defaults(func=handle_share)
