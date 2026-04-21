import os
import re
import sys
import json
import time


def _skill_dir():
    # python/scripts/api.py → skill root is two dirs up
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def load_env():
    home = os.path.expanduser("~")
    skill = _skill_dir()
    env_files = [
        # 用户家目录（优先级最高）
        os.path.join(home, ".outline.env"),
        os.path.join(home, ".env"),
        # cwd（项目级覆盖）
        ".outline.env",
        ".env",
        # skill 目录（本仓库自带配置）
        os.path.join(skill, ".outline.env"),
        os.path.join(skill, ".env"),
    ]
    seen = set()
    for env_file in env_files:
        env_file = os.path.abspath(env_file)
        if env_file in seen or not os.path.exists(env_file):
            continue
        seen.add(env_file)
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.strip().split("=", 1)
                    if key not in os.environ:
                        os.environ[key] = value.strip("\"'")


load_env()
BASE_URL = (os.environ.get("OUTLINE_BASE_URL") or "").rstrip("/")
API_KEY = os.environ.get("OUTLINE_API_KEY")

DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3

_HUMAN_HINTS = {
    400: "请求参数错误：检查必填字段、ID 格式、JSON 结构。Outline 通常会在 raw.error 里给具体原因。",
    401: "认证失败：OUTLINE_API_KEY 无效或已过期。",
    403: "权限不足：当前 API key 无权访问该资源（可能不在协作者列表 / 不是管理员）。",
    404: "资源不存在：请检查 ID 或 URL 是否正确，或文档是否被删除。",
    422: "校验失败：参数值不合法（如枚举超范围、长度超限）。看 raw.error 里的 message 字段。",
    429: "触发限流：请求过快，已自动重试仍失败，请增大延迟或稍后重试。",
    500: "Outline 服务器内部错误。已自动重试仍失败。可稍后重试或联系管理员。",
    502: "网关错误：Outline 上游异常。已自动重试。",
    503: "服务暂不可用：Outline 可能在维护 / 重启。已自动重试。",
    504: "网关超时：Outline 响应太慢。已自动重试。",
}

_client = None


def _ensure_ready():
    """Lazy-load httpx + validate env. Allows non-network commands to run without setup."""
    global _client
    if not BASE_URL or not API_KEY:
        home_env = os.path.join(os.path.expanduser("~"), ".outline.env")
        msg = (
            f"未找到环境配置。系统已优先检查过用户目录 ({home_env})，"
            "并依次查找了当前执行目录及 Skill 目录，但均未发现 .outline.env 或 .env 文件。\\n"
            "请在用户目录下创建 .outline.env，并填入 OUTLINE_BASE_URL 和 OUTLINE_API_KEY 进行配置。"
        )
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": msg,
                },
                ensure_ascii=False,
            )
        )
        sys.exit(1)
    if _client is None:
        try:
            import httpx  # noqa
        except ImportError:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": "缺少 httpx 库。请用 run.sh 启动（自动通过 uv 注入），或手动安装：pip install httpx -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple",
                    },
                    ensure_ascii=False,
                )
            )
            sys.exit(1)
        _client = httpx.Client(
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=True,
        )
    return _client


def _make_error(status, body, endpoint):
    return {
        "ok": False,
        "status": status,
        "endpoint": endpoint,
        "hint": _HUMAN_HINTS.get(status, ""),
        "raw": body if isinstance(body, (dict, list)) else str(body)[:500],
    }


def api_post(endpoint, payload=None):
    """POST to /api/{endpoint} with retry on 429/5xx and human-friendly errors."""
    import httpx
    client = _ensure_ready()
    url = f"{BASE_URL}/api/{endpoint}"
    body = payload or {}

    for attempt in range(MAX_RETRIES):
        try:
            res = client.post(url, json=body)
        except httpx.RequestError as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            return {
                "ok": False, "status": 0, "endpoint": endpoint,
                "hint": "网络错误，已重试多次仍失败。", "error": str(e),
            }

        if res.status_code == 429 or 500 <= res.status_code < 600:
            if attempt < MAX_RETRIES - 1:
                retry_after = res.headers.get("Retry-After")
                wait = float(retry_after) if retry_after else 2 ** attempt
                time.sleep(wait)
                continue

        try:
            data = res.json()
        except Exception:
            data = {"text": res.text}

        if res.status_code >= 400:
            return _make_error(res.status_code, data, endpoint)
        return data

    return {"ok": False, "endpoint": endpoint, "hint": "重试用尽。"}


# ---- pagination helper -----------------------------------------------------
def paginate_all(endpoint, payload=None, page_size=100, max_items=None):
    """Iterate all pages and return a synthetic response {ok:True, data:[...], count:N}.

    Stops when returned batch is smaller than page_size (last page) or when
    max_items reached. Safe to use on any endpoint that accepts offset/limit
    and returns {data: [...]}.
    """
    body = dict(payload or {})
    body.setdefault("limit", page_size)
    offset = int(body.get("offset") or 0)
    limit = int(body["limit"])
    items = []
    while True:
        body["offset"] = offset
        body["limit"] = limit
        res = api_post(endpoint, body)
        if isinstance(res, dict) and res.get("ok") is False:
            return res
        batch = res.get("data") if isinstance(res, dict) else None
        if not isinstance(batch, list):
            return res
        items.extend(batch)
        if len(batch) < limit:
            break
        if max_items is not None and len(items) >= max_items:
            items = items[:max_items]
            break
        offset += limit
    return {"ok": True, "data": items, "count": len(items), "paginated": True}


# ---- ID extraction ---------------------------------------------------------
_URL_DOC_RE = re.compile(r"/doc(?:ument)?/(?:.*?-)?([A-Za-z0-9]{10,})", re.IGNORECASE)
_URL_COLL_RE = re.compile(r"/collection(?:s)?/(?:.*?-)?([A-Za-z0-9-]{8,})", re.IGNORECASE)


def extract_id(value, kind="doc"):
    """Accept either a raw ID or an Outline URL. Returns the ID portion.
    kind: 'doc' or 'collection' — selects which regex to try first.
    """
    if not value:
        return value
    s = str(value).strip()
    if "://" not in s and "/" not in s:
        return s
    pat = _URL_DOC_RE if kind == "doc" else _URL_COLL_RE
    m = pat.search(s)
    if m:
        return m.group(1)
    tail = s.rstrip("/").split("/")[-1]
    if "-" in tail:
        tail = tail.split("-")[-1]
    return tail
