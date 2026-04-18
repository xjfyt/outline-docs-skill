"""revision subcommand — read document revision history (read-only)."""
import sys
from .api import api_post, extract_id
from .utils import render_response, print_json


def _summ_revision(r, preview_len=120):
    if not isinstance(r, dict):
        return r
    by = r.get("createdBy") or {}
    out = {
        "id": r.get("id"),
        "documentId": r.get("documentId"),
        "title": r.get("title"),
        "createdBy": {"id": by.get("id"), "name": by.get("name")},
        "createdAt": r.get("createdAt"),
    }
    if preview_len and preview_len > 0:
        t = r.get("text") or ""
        out["textPreview"] = t[:preview_len] + "…" if len(t) > preview_len else t
    return out


def handle_revision(args):
    if args.action == "list":
        if not args.document_id:
            print_json({"ok": False, "error": "需要 --document-id"}); sys.exit(1)
        payload = {"documentId": extract_id(args.document_id, "doc")}
        if getattr(args, "limit", None): payload["limit"] = args.limit
        if getattr(args, "offset", None): payload["offset"] = args.offset
        res = api_post("revisions.list", payload)
        render_response(res, summarizer=_summ_revision, full=args.full)

    elif args.action == "info":
        if not args.id:
            print_json({"ok": False, "error": "需要 --id"}); sys.exit(1)
        res = api_post("revisions.info", {"id": args.id})
        render_response(res, summarizer=_summ_revision, full=args.full)


def setup_revision_parser(subparsers):
    p = subparsers.add_parser("revision", help="文档历史版本（只读）")
    p.add_argument("action", choices=["list", "info"])
    p.add_argument("--id", help="revision ID")
    p.add_argument("--document-id", help="文档 ID 或 URL")
    p.add_argument("--limit", type=int)
    p.add_argument("--offset", type=int)
    p.add_argument("--full", action="store_true")
    p.set_defaults(func=handle_revision)
