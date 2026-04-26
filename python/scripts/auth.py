"""auth subcommand — health check / show current workspace + user."""
import os
import platform
import sys
from .api import (
    api_post,
    BASE_URL,
    CONFIG_ERROR,
    CURRENT_INSTANCE,
    DANGEROUS_OPERATION_PROTECTION,
    INSTANCE_SUMMARIES,
)
from .utils import print_json, render_response

SKILL_VERSION = "1.2.0"


def _runtime_info():
    try:
        import httpx  # noqa: F401
        httpx_ver = getattr(sys.modules["httpx"], "__version__", "unknown")
    except Exception:
        httpx_ver = None
    return {
        "lang": "python",
        "python": platform.python_version(),
        "httpx": httpx_ver,
        "runVia": os.environ.get("OUTLINE_RUN_VIA") or "auto",
        "platform": platform.system().lower(),
    }


def handle_auth(args):
    if args.action == "info":
        res = api_post("auth.info")
        if isinstance(res, dict) and res.get("ok") is False:
            print_json(res)
            return
        data = res.get("data", {}) if isinstance(res, dict) else {}
        user = data.get("user") or {}
        team = data.get("team") or {}
        print_json(
            {
                "ok": True,
                "baseUrl": BASE_URL,
                "outlineInstance": CURRENT_INSTANCE,
                "dangerousOperationProtection": DANGEROUS_OPERATION_PROTECTION,
                "skillVersion": SKILL_VERSION,
                "runtime": _runtime_info(),
                "user": {
                    "id": user.get("id"),
                    "name": user.get("name"),
                    "email": user.get("email"),
                    "role": user.get("role"),
                },
                "team": {
                    "id": team.get("id"),
                    "name": team.get("name"),
                    "url": team.get("url"),
                },
            }
        )
    elif args.action == "config":
        render_response(api_post("auth.config"), full=True)
    elif args.action == "instances":
        if CONFIG_ERROR:
            print_json({"ok": False, "error": CONFIG_ERROR})
            sys.exit(1)
        print_json(
            {
                "ok": True,
                "dangerousOperationProtection": DANGEROUS_OPERATION_PROTECTION,
                "current": CURRENT_INSTANCE,
                "items": INSTANCE_SUMMARIES,
            }
        )


def setup_auth_parser(subparsers):
    p = subparsers.add_parser("auth", help="检查认证 / 当前工作区信息")
    p.add_argument("action", choices=["info", "config", "instances"])
    p.set_defaults(func=handle_auth)
