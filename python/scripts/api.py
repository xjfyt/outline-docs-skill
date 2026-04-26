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
        # cwd（项目级配置）
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


def _instance_config_files():
    configured = os.environ.get("OUTLINE_INSTANCES_FILE")
    if configured:
        return [configured]
    home = os.path.expanduser("~")
    skill = _skill_dir()
    return [
        os.path.join(home, ".outline.instances.json"),
        ".outline.instances.json",
        os.path.join(skill, ".outline.instances.json"),
    ]


def _load_instance_config():
    seen = set()
    explicit = bool(os.environ.get("OUTLINE_INSTANCES_FILE"))
    for config_file in _instance_config_files():
        config_file = os.path.abspath(os.path.expanduser(config_file))
        if config_file in seen:
            continue
        seen.add(config_file)
        if not os.path.exists(config_file):
            if explicit:
                raise FileNotFoundError(f"OUTLINE_INSTANCES_FILE 指向的文件不存在：{config_file}")
            continue
        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(f"{config_file} 必须是 JSON object")
        return data, config_file
    return {}, None


def _pick_first(raw, keys):
    for key in keys:
        value = raw.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _pick_env(raw, keys):
    env_name = _pick_first(raw, keys)
    if not env_name:
        return None
    return os.environ.get(env_name)


def _normalize_aliases(raw):
    aliases = []
    for key in ["aliases", "alias"]:
        value = raw.get(key)
        if not value:
            continue
        if isinstance(value, str):
            aliases.append(value.strip())
        elif isinstance(value, list):
            aliases.extend(str(item).strip() for item in value if str(item).strip())
        else:
            aliases.append(str(value).strip())
    return [alias for alias in aliases if alias]


def _bool_config(raw, keys, default=False):
    for key in keys:
        if key not in raw:
            continue
        value = raw.get(key)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on", "enabled", "开启"}
        return bool(value)
    return default


def _normalize_instance(raw, key=None):
    if not isinstance(raw, dict):
        raise ValueError(f"实例 {key or '<unknown>'} 必须是 JSON object")
    name = str(key or raw.get("name") or "").strip()
    if not name:
        raise ValueError("每个实例都必须有 name")
    display_name = _pick_first(raw, ["displayName", "display_name", "label"]) or str(raw.get("name") or name)
    base_url = _pick_env(raw, ["baseUrlEnv", "base_url_env", "urlEnv", "url_env"])
    api_key = _pick_env(raw, ["apiKeyEnv", "api_key_env", "tokenEnv", "token_env"])
    base_url = base_url or _pick_first(raw, ["baseUrl", "base_url", "url"])
    api_key = api_key or _pick_first(raw, ["apiKey", "api_key", "token"])
    return {
        "name": name,
        "displayName": display_name,
        "aliases": _normalize_aliases(raw),
        "baseUrl": (base_url or "").rstrip("/"),
        "apiKey": api_key or "",
    }


def _normalize_instances(config):
    raw_instances = config.get("instances") or {}
    instances = {}
    if isinstance(raw_instances, dict):
        for key, raw in raw_instances.items():
            item = _normalize_instance(raw, str(key))
            instances[item["name"]] = item
    elif isinstance(raw_instances, list):
        for raw in raw_instances:
            item = _normalize_instance(raw)
            instances[item["name"]] = item
    else:
        raise ValueError("instances 必须是 object 或 array")
    _validate_instance_selectors(instances)
    return instances


def _validate_instance_selectors(instances):
    seen = {}
    for name, instance in instances.items():
        selectors = [name, instance.get("displayName"), *(instance.get("aliases") or [])]
        for selector in selectors:
            if not selector:
                continue
            owner = seen.get(selector)
            if owner and owner != name:
                raise ValueError(f"Outline 实例选择器重复：{selector} 同时指向 {owner} 和 {name}")
            seen[selector] = name


def _config_default_name(config):
    return _pick_first(config, ["default", "defaultInstance", "default_instance"])


def _find_instance(instances, selected_name):
    if selected_name in instances:
        return instances[selected_name], selected_name
    for name, instance in instances.items():
        candidates = [instance.get("displayName"), *(instance.get("aliases") or [])]
        if selected_name in candidates:
            return instance, name
    return None, selected_name


def _resolve_settings():
    env_base_url = (os.environ.get("OUTLINE_BASE_URL") or "").rstrip("/")
    env_api_key = os.environ.get("OUTLINE_API_KEY") or ""
    try:
        config, config_path = _load_instance_config()
        instances = _normalize_instances(config)
        config_error = None
    except Exception as e:
        config, config_path, instances = {}, None, {}
        config_error = f"读取 Outline 多实例配置失败：{e}"

    default_input = (
        os.environ.get("OUTLINE_INSTANCE_NAME")
        or _config_default_name(config)
        or "default"
    ).strip()
    _, default_name = _find_instance(instances, default_input)
    selected_input = (os.environ.get("OUTLINE_INSTANCE") or default_name).strip()
    if selected_input in ("default", "env") and selected_input not in instances:
        selected_input = default_name

    instance, selected_name = _find_instance(instances, selected_input)
    is_default = selected_name == default_name
    dangerous_protection = _bool_config(
        config,
        ["dangerousOperationProtection", "dangerous_operation_protection", "protectDangerousOperations"],
        False,
    )
    if instance:
        dangerous_protection = _bool_config(
            instance,
            ["dangerousOperationProtection", "dangerous_operation_protection", "protectDangerousOperations"],
            dangerous_protection,
        )
        if is_default:
            base_url = env_base_url or instance["baseUrl"]
            api_key = env_api_key or instance["apiKey"]
        else:
            base_url = instance["baseUrl"]
            api_key = instance["apiKey"]
    elif is_default:
        base_url = env_base_url
        api_key = env_api_key
    else:
        base_url = ""
        api_key = ""

    instance_error = None
    if not instance and not is_default:
        instance_error = (
            f"未找到 Outline 实例：{selected_input}。请在 .outline.instances.json 的 instances 中配置该名称，"
            "或使用实例的 name / displayName / aliases。"
        )
    elif instance and not is_default and (not base_url or not api_key):
        missing = []
        if not base_url:
            missing.append("baseUrl")
        if not api_key:
            missing.append("apiKey")
        instance_error = f"Outline 实例 {selected_name} 缺少 {', '.join(missing)}。"

    current = {
        "name": selected_name,
        "displayName": (instance or {}).get("displayName") or selected_name,
        "default": is_default,
        "configPath": config_path,
    }
    if selected_input != selected_name:
        current["requested"] = selected_input
    summaries = _build_instance_summaries(instances, default_name, selected_name, env_base_url, env_api_key, config_path)
    return base_url, api_key, current, config_error or instance_error, dangerous_protection, summaries


def _build_instance_summaries(instances, default_name, selected_name, env_base_url, env_api_key, config_path):
    summaries = []
    names = list(instances.keys())
    if default_name not in instances:
        names.insert(0, default_name)
    for name in names:
        instance = instances.get(name) or {}
        is_default = name == default_name
        base_url = (env_base_url or instance.get("baseUrl") or "") if is_default else (instance.get("baseUrl") or "")
        api_key = (env_api_key or instance.get("apiKey") or "") if is_default else (instance.get("apiKey") or "")
        summaries.append(
            {
                "name": name,
                "displayName": instance.get("displayName") or name,
                "aliases": instance.get("aliases") or [],
                "baseUrl": base_url,
                "hasApiKey": bool(api_key),
                "default": is_default,
                "current": name == selected_name,
                "configPath": config_path,
            }
        )
    return summaries


load_env()
BASE_URL, API_KEY, CURRENT_INSTANCE, CONFIG_ERROR, DANGEROUS_OPERATION_PROTECTION, INSTANCE_SUMMARIES = _resolve_settings()
INSTANCE_NAME = CURRENT_INSTANCE["name"]


def require_danger_confirmation(operation, confirmed=False):
    if not DANGEROUS_OPERATION_PROTECTION or confirmed:
        return
    print(
        json.dumps(
            {
                "ok": False,
                "error": "危险操作保护已开启，需要显式确认后才能执行。",
                "operation": operation,
                "requiredFlag": "--confirm",
                "hint": "如确认要执行，请重新运行命令并添加 --confirm 或 --confirm-dangerous。",
            },
            ensure_ascii=False,
        )
    )
    sys.exit(1)

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
    if CONFIG_ERROR:
        print(json.dumps({"ok": False, "error": CONFIG_ERROR}, ensure_ascii=False))
        sys.exit(1)
    if not BASE_URL or not API_KEY:
        home_env = os.path.join(os.path.expanduser("~"), ".outline.env")
        msg = (
            f"未找到环境配置。系统已优先检查过用户目录 ({home_env})，"
            "并依次查找了当前执行目录及 Skill 目录，但均未发现 .outline.env 或 .env 文件。\\n"
            "请在用户目录下创建 .outline.env，并填入 OUTLINE_BASE_URL 和 OUTLINE_API_KEY 作为默认实例；"
            "多实例可在 .outline.instances.json 中配置，并用 OUTLINE_INSTANCE 或 --instance 选择。"
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
        "outlineInstance": CURRENT_INSTANCE,
        "hint": _HUMAN_HINTS.get(status, ""),
        "raw": body if isinstance(body, (dict, list)) else str(body)[:500],
    }


def api_post(endpoint, payload=None):
    """POST to /api/{endpoint} with retry on 429/5xx and human-friendly errors."""
    client = _ensure_ready()
    import httpx
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
                "outlineInstance": CURRENT_INSTANCE,
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
