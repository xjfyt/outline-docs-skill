"""comment subcommand — read/write comments on documents."""
import sys
from .api import api_post, extract_id
from .utils import render_response, print_json


def _summ_comment(c, preview_len=200):
    if not isinstance(c, dict):
        return c
    text = c.get("data", "") if isinstance(c.get("data"), str) else c.get("text", "")
    if isinstance(text, str) and preview_len and len(text) > preview_len:
        text = text[:preview_len] + "…"
    created_by = c.get("createdBy") or {}
    return {
        "id": c.get("id"),
        "documentId": c.get("documentId"),
        "parentCommentId": c.get("parentCommentId"),
        "createdBy": {"id": created_by.get("id"), "name": created_by.get("name")},
        "createdAt": c.get("createdAt"),
        "updatedAt": c.get("updatedAt"),
        "text": text,
    }


def handle_comment(args):
    if args.action == "list":
        if not args.document_id:
            print_json({"ok": False, "error": "需要 --document-id"}); sys.exit(1)
        payload = {"documentId": extract_id(args.document_id, "doc")}
        if getattr(args, "limit", None): payload["limit"] = args.limit
        if getattr(args, "offset", None): payload["offset"] = args.offset
        res = api_post("comments.list", payload)
        render_response(res, summarizer=_summ_comment, full=args.full)

    elif args.action == "info":
        if not args.id:
            print_json({"ok": False, "error": "需要 --id"}); sys.exit(1)
        res = api_post("comments.info", {"id": args.id})
        render_response(res, summarizer=_summ_comment, full=args.full)

    elif args.action == "create":
        if not args.document_id or not args.text:
            print_json({"ok": False, "error": "需要 --document-id 与 --text"}); sys.exit(1)
        payload = {
            "documentId": extract_id(args.document_id, "doc"),
            "data": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": args.text}]}]},
        }
        if args.parent_comment_id: payload["parentCommentId"] = args.parent_comment_id
        res = api_post("comments.create", payload)
        render_response(res, summarizer=_summ_comment, full=args.full)

    elif args.action == "update":
        if not args.id or not args.text:
            print_json({"ok": False, "error": "需要 --id 与 --text"}); sys.exit(1)
        payload = {
            "id": args.id,
            "data": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": args.text}]}]},
        }
        res = api_post("comments.update", payload)
        render_response(res, summarizer=_summ_comment, full=args.full)

    elif args.action == "delete":
        if not args.id:
            print_json({"ok": False, "error": "需要 --id"}); sys.exit(1)
        res = api_post("comments.delete", {"id": args.id})
        render_response(res, full=True)


def setup_comment_parser(subparsers):
    p = subparsers.add_parser("comment", help="管理文档评论")
    p.add_argument("action", choices=["list", "info", "create", "update", "delete"])
    p.add_argument("--id", help="comment ID（info/update/delete 用）")
    p.add_argument("--document-id", help="文档 ID 或 URL（list/create 用）")
    p.add_argument("--parent-comment-id", help="create：回复某条评论时传")
    p.add_argument("--text", help="create/update：评论文本（纯文本；会自动包装成 ProseMirror 节点）")
    p.add_argument("--limit", type=int)
    p.add_argument("--offset", type=int)
    p.add_argument("--full", action="store_true")
    p.set_defaults(func=handle_comment)
