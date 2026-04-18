import os
import sys
import json
import mimetypes
import time
from .api import api_post, extract_id


def _post_file(upload_url, form_data, filepath, timeout=30):
    """S3-style multipart upload (separate from Outline API auth)."""
    import httpx
    with open(filepath, "rb") as f:
        files = {"file": (os.path.basename(filepath), f)}
        return httpx.post(upload_url, data=form_data, files=files, timeout=timeout)


def handle_upload(args):
    filepath = args.filepath
    document_id = extract_id(args.document_id, "doc")
    if not os.path.exists(filepath):
        print(json.dumps({"ok": False, "error": f"File not found: {filepath}"}, ensure_ascii=False))
        sys.exit(1)

    size = os.path.getsize(filepath)
    name = os.path.basename(filepath)
    content_type, _ = mimetypes.guess_type(filepath)
    if not content_type:
        content_type = "application/octet-stream"

    payload = {
        "name": name,
        "size": size,
        "contentType": content_type,
        "documentId": document_id,
    }

    res = api_post("attachments.create", payload)
    if not res.get("ok"):
        print(json.dumps(res, indent=2, ensure_ascii=False))
        sys.exit(1)

    upload_url = res["data"]["uploadUrl"]
    form_data = res["data"]["form"]
    attachment_url = res["data"]["attachment"]["url"]

    upload_res = _post_file(upload_url, form_data, filepath)

    if upload_res.status_code in (200, 204):
        print(
            json.dumps(
                {
                    "ok": True,
                    "attachment_url": attachment_url,
                    "markdown": f"![{name}]({attachment_url})",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(json.dumps({"ok": False, "status": upload_res.status_code, "error": upload_res.text}, ensure_ascii=False))


def upload_image_for_document(filepath, document_id, max_retries=3):
    """Used by upload_dir to upload local images referenced in markdown."""
    import httpx
    if not os.path.exists(filepath):
        return None

    size = os.path.getsize(filepath)
    name = os.path.basename(filepath)
    content_type, _ = mimetypes.guess_type(filepath)
    if not content_type:
        content_type = "application/octet-stream"

    payload = {
        "name": name,
        "size": size,
        "contentType": content_type,
        "documentId": document_id,
    }

    for attempt in range(max_retries):
        try:
            res = api_post("attachments.create", payload)
            if not res.get("ok"):
                print(f"Failed to get upload URL for {filepath}: {res}")
                return None

            upload_url = res["data"]["uploadUrl"]
            form_data = res["data"]["form"]
            attachment_url = res["data"]["attachment"]["url"]

            upload_res = _post_file(upload_url, form_data, filepath, timeout=60)

            if upload_res.status_code in (200, 204):
                return attachment_url
            print(f"Failed to upload {filepath}: {upload_res.status_code} {upload_res.text[:200]}")
            return None

        except httpx.RequestError as e:
            if attempt < max_retries - 1:
                print(f"Connection error uploading {filepath}, retrying ({attempt + 1}/{max_retries})...")
                time.sleep(2)
            else:
                print(f"Failed to upload {filepath} after {max_retries} attempts: {e}")
                return None
    return None


def setup_attachment_parser(subparsers):
    p = subparsers.add_parser("upload", help="向某文档上传附件/图片")
    p.add_argument("--filepath", required=True, help="本地文件路径")
    p.add_argument("--document-id", required=True, help="文档 ID 或 URL")
    p.set_defaults(func=handle_upload)
