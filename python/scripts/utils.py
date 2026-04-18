"""Shared output helpers — keep CLI output compact to save Claude's tokens."""
import json
import sys


def print_json(data, indent=2):
    """Print JSON with UTF-8 (no \\uXXXX escapes for CJK)."""
    print(json.dumps(data, indent=indent, ensure_ascii=False))


def _truncate(s, n):
    if not isinstance(s, str) or n is None or n <= 0:
        return None if (n is not None and n <= 0) else s
    return s if len(s) <= n else s[:n] + "…"


def summarize_doc(doc, preview_len=120):
    """Strip a document object to the fields Claude actually needs.
    preview_len=0 drops textPreview entirely (even more compact)."""
    if not isinstance(doc, dict):
        return doc
    out = {
        "id": doc.get("id"),
        "title": doc.get("title"),
        "url": doc.get("url"),
        "collectionId": doc.get("collectionId"),
        "parentDocumentId": doc.get("parentDocumentId"),
        "updatedAt": doc.get("updatedAt"),
        "archivedAt": doc.get("archivedAt"),
        "publishedAt": doc.get("publishedAt"),
    }
    if preview_len and preview_len > 0:
        out["textPreview"] = _truncate(doc.get("text") or "", preview_len)
    return out


def summarize_collection(coll, preview_len=100):
    if not isinstance(coll, dict):
        return coll
    out = {
        "id": coll.get("id"),
        "name": coll.get("name"),
        "url": coll.get("url"),
        "permission": coll.get("permission"),
        "updatedAt": coll.get("updatedAt"),
    }
    if preview_len and preview_len > 0:
        out["description"] = _truncate(coll.get("description") or "", preview_len)
    return out


def _resolve_preview_len(args, default):
    v = getattr(args, "preview_len", None)
    if v is None or v == "":
        return default
    try:
        return max(0, int(v))
    except (TypeError, ValueError):
        return default


def render_response(res, summarizer=None, full=False, args=None, default_preview=120):
    """Print an Outline API response.

    - On error, prints raw error JSON and exits non-zero.
    - On list response (data is list), summarize each item unless --full.
    - On single-object response, summarize unless --full.
    """
    if isinstance(res, dict) and res.get("ok") is False:
        print_json(res)
        sys.exit(1)

    if full or not summarizer:
        print_json(res)
        return

    preview_len = _resolve_preview_len(args, default_preview) if args is not None else default_preview

    def call(item):
        try:
            return summarizer(item, preview_len=preview_len)
        except TypeError:
            return summarizer(item)

    data = res.get("data") if isinstance(res, dict) else res
    if isinstance(data, list):
        out = {
            "ok": True,
            "count": len(data),
            "items": [call(x) for x in data],
        }
        if isinstance(res, dict) and res.get("pagination"):
            out["pagination"] = res["pagination"]
        print_json(out)
    elif isinstance(data, dict):
        print_json({"ok": True, "data": call(data)})
    else:
        print_json(res)
