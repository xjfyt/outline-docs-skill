"""api subcommand — raw Outline API escape hatch.

用于访问本 skill 尚未封装的端点（如 stars.*, fileOperations.*, groups.* 等）。
用法：
    bash bin/run.sh api call --endpoint documents.info --data '{"id":"..."}'
    bash bin/run.sh api call --endpoint stars.list

默认会把响应按摘要处理，除非 --full。
"""
import json
import sys
from .api import api_post, paginate_all
from .utils import print_json


def handle_api(args):
    if args.action != "call":
        print_json({"ok": False, "error": "仅支持 'api call'（通用 POST 端点）"}); sys.exit(2)

    if not args.endpoint:
        print_json({
            "ok": False,
            "error": "需要 --endpoint <name>（如 documents.info / stars.list / fileOperations.list）",
            "docs": "https://www.getoutline.com/developers",
        })
        sys.exit(1)

    payload = {}
    if args.data:
        try:
            payload = json.loads(args.data)
        except json.JSONDecodeError as e:
            print_json({"ok": False, "error": f"--data 不是合法 JSON：{e}"})
            sys.exit(1)
        if not isinstance(payload, dict):
            print_json({"ok": False, "error": "--data 必须是 JSON 对象（{...}）"})
            sys.exit(1)
    if args.data_file:
        import os
        if not os.path.exists(args.data_file):
            print_json({"ok": False, "error": f"--data-file 不存在：{args.data_file}"})
            sys.exit(1)
        with open(args.data_file, "r", encoding="utf-8") as f:
            try:
                payload = json.load(f)
            except json.JSONDecodeError as e:
                print_json({"ok": False, "error": f"--data-file 不是合法 JSON：{e}"})
                sys.exit(1)

    if args.all:
        res = paginate_all(args.endpoint, payload)
    else:
        res = api_post(args.endpoint, payload)
    print_json(res)


def setup_api_parser(subparsers):
    p = subparsers.add_parser(
        "api",
        help="通用 API 调用（覆盖本 skill 未封装的端点，如 stars/fileOperations/groups 等）",
    )
    p.add_argument("action", choices=["call"])
    p.add_argument("--endpoint", help="Outline 端点名，例：documents.info / stars.list")
    p.add_argument("--data", help="payload JSON 字符串（如 '{\"id\":\"...\"}'）")
    p.add_argument("--data-file", help="从文件读 payload JSON（适合长 payload）")
    p.add_argument("--all", action="store_true", help="如果返回 data 是列表，自动翻页累积")
    p.set_defaults(func=handle_api)
