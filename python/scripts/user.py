"""user subcommand — read team members (for @mentions, permissions, etc.)."""
import sys
from .api import api_post, paginate_all
from .utils import render_response, print_json


def _summ_user(u, preview_len=None):
    if not isinstance(u, dict):
        return u
    return {
        "id": u.get("id"),
        "name": u.get("name"),
        "email": u.get("email"),
        "role": u.get("role"),
        "isSuspended": u.get("isSuspended"),
        "lastActiveAt": u.get("lastActiveAt"),
    }


def handle_user(args):
    if args.action == "list":
        payload = {}
        if getattr(args, "limit", None): payload["limit"] = args.limit
        if getattr(args, "offset", None): payload["offset"] = args.offset
        if getattr(args, "query", None): payload["query"] = args.query
        if getattr(args, "filter", None): payload["filter"] = args.filter
        res = paginate_all("users.list", payload) if getattr(args, "all", False) else api_post("users.list", payload)
        render_response(res, summarizer=_summ_user, full=args.full)

    elif args.action == "info":
        if not args.id:
            print_json({"ok": False, "error": "需要 --id"}); sys.exit(1)
        res = api_post("users.info", {"id": args.id})
        render_response(res, summarizer=_summ_user, full=args.full)


def setup_user_parser(subparsers):
    p = subparsers.add_parser("user", help="团队成员（用于 @mention / 权限查询）")
    p.add_argument("action", choices=["list", "info"])
    p.add_argument("--id", help="用户 ID")
    p.add_argument("--query", help="list：按名称/邮箱搜索")
    p.add_argument("--filter", choices=["active", "admins", "members", "suspended", "invited", "all"],
                   help="list：状态筛选")
    p.add_argument("--limit", type=int)
    p.add_argument("--offset", type=int)
    p.add_argument("--all", action="store_true", help="list：自动翻页累积所有用户")
    p.add_argument("--full", action="store_true")
    p.set_defaults(func=handle_user)
