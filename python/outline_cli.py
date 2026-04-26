import argparse
import json
import os
import sys


def _apply_instance_flag(argv):
    cleaned = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--instance", "--outline-instance"):
            if i + 1 >= len(argv) or argv[i + 1].startswith("-"):
                print(json.dumps({"ok": False, "error": "--instance 需要实例名"}, ensure_ascii=False))
                sys.exit(2)
            os.environ["OUTLINE_INSTANCE"] = argv[i + 1]
            i += 2
            continue
        if arg.startswith("--instance="):
            os.environ["OUTLINE_INSTANCE"] = arg.split("=", 1)[1]
            i += 1
            continue
        if arg.startswith("--outline-instance="):
            os.environ["OUTLINE_INSTANCE"] = arg.split("=", 1)[1]
            i += 1
            continue
        cleaned.append(arg)
        i += 1
    return cleaned


sys.argv = [sys.argv[0]] + _apply_instance_flag(sys.argv[1:])

from scripts.auth import setup_auth_parser
from scripts.collection import setup_collection_parser
from scripts.document import setup_document_parser
from scripts.attachment import setup_attachment_parser
from scripts.upload_dir import setup_upload_dir_parser
from scripts.template import setup_template_parser
from scripts.share import setup_share_parser
from scripts.comment import setup_comment_parser
from scripts.revision import setup_revision_parser
from scripts.user import setup_user_parser
from scripts.pin import setup_pin_parser
from scripts.generic import setup_api_parser


def main():
    parser = argparse.ArgumentParser(
        description="Outline API CLI —— 管理 Outline 知识库（集合 / 文档 / 附件 / 模板 / 分享 / 评论 / 版本 / 成员 / 置顶 / 通用 API）",
        epilog="多实例：任意位置添加 --instance <name>，或设置 OUTLINE_INSTANCE=<name>。",
    )
    subparsers = parser.add_subparsers(dest="resource", required=True)

    setup_auth_parser(subparsers)
    setup_collection_parser(subparsers)
    setup_document_parser(subparsers)
    setup_attachment_parser(subparsers)
    setup_upload_dir_parser(subparsers)
    setup_template_parser(subparsers)
    setup_share_parser(subparsers)
    setup_comment_parser(subparsers)
    setup_revision_parser(subparsers)
    setup_user_parser(subparsers)
    setup_pin_parser(subparsers)
    setup_api_parser(subparsers)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
