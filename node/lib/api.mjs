import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";

function skillDir() {
  // node/lib/api.mjs → skill root is two dirs up
  return path.normalize(path.join(path.dirname(fileURLToPath(import.meta.url)), "..", ".."));
}

export function loadEnv() {
  const skill = skillDir();
  const home = os.homedir();
  const files = [
    // 用户家目录（优先级最高）
    path.join(home, ".outline.env"),
    path.join(home, ".env"),
    // cwd（项目级配置）
    ".outline.env",
    ".env",
    // skill 目录（本仓库自带配置）
    path.join(skill, ".outline.env"),
    path.join(skill, ".env"),
  ];
  const seen = new Set();
  for (const f of files) {
    const abs = path.resolve(f);
    if (seen.has(abs) || !fs.existsSync(abs)) continue;
    seen.add(abs);
    const content = fs.readFileSync(abs, "utf8");
    for (const line of content.split(/\r?\n/)) {
      const t = line.trim();
      if (!t || t.startsWith("#") || !t.includes("=")) continue;
      const idx = t.indexOf("=");
      const k = t.slice(0, idx).trim();
      let v = t.slice(idx + 1).trim();
      if ((v.startsWith('"') && v.endsWith('"')) || (v.startsWith("'") && v.endsWith("'"))) {
        v = v.slice(1, -1);
      }
      if (!(k in process.env)) process.env[k] = v;
    }
  }
}

function instanceConfigFiles() {
  if (process.env.OUTLINE_INSTANCES_FILE) return [process.env.OUTLINE_INSTANCES_FILE];
  const skill = skillDir();
  const home = os.homedir();
  return [
    path.join(home, ".outline.instances.json"),
    ".outline.instances.json",
    path.join(skill, ".outline.instances.json"),
  ];
}

function loadInstanceConfig() {
  const seen = new Set();
  const explicit = Boolean(process.env.OUTLINE_INSTANCES_FILE);
  for (const f of instanceConfigFiles()) {
    const configPath = path.resolve(f.replace(/^~(?=$|[/\\])/, os.homedir()));
    if (seen.has(configPath)) continue;
    seen.add(configPath);
    if (!fs.existsSync(configPath)) {
      if (explicit) throw new Error(`OUTLINE_INSTANCES_FILE 指向的文件不存在：${configPath}`);
      continue;
    }
    const data = JSON.parse(fs.readFileSync(configPath, "utf8"));
    if (!data || typeof data !== "object" || Array.isArray(data)) {
      throw new Error(`${configPath} 必须是 JSON object`);
    }
    return { config: data, configPath };
  }
  return { config: {}, configPath: null };
}

function pickFirst(raw, keys) {
  for (const key of keys) {
    const value = raw[key];
    if (value !== undefined && value !== null && String(value).trim()) {
      return String(value).trim();
    }
  }
  return null;
}

function pickEnv(raw, keys) {
  const envName = pickFirst(raw, keys);
  return envName ? process.env[envName] : null;
}

function normalizeAliases(raw) {
  const aliases = [];
  for (const key of ["aliases", "alias"]) {
    const value = raw[key];
    if (!value) continue;
    if (typeof value === "string") {
      aliases.push(value.trim());
    } else if (Array.isArray(value)) {
      aliases.push(...value.map((item) => String(item).trim()).filter(Boolean));
    } else {
      aliases.push(String(value).trim());
    }
  }
  return aliases.filter(Boolean);
}

function normalizeInstance(raw, key = null) {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new Error(`实例 ${key || "<unknown>"} 必须是 JSON object`);
  }
  const name = String(key || raw.name || "").trim();
  if (!name) throw new Error("每个实例都必须有 name");
  const displayName = pickFirst(raw, ["displayName", "display_name", "label"]) || String(raw.name || name);
  const baseUrl = (
    pickEnv(raw, ["baseUrlEnv", "base_url_env", "urlEnv", "url_env"])
    || pickFirst(raw, ["baseUrl", "base_url", "url"])
    || ""
  ).replace(/\/$/, "");
  const apiKey = (
    pickEnv(raw, ["apiKeyEnv", "api_key_env", "tokenEnv", "token_env"])
    || pickFirst(raw, ["apiKey", "api_key", "token"])
    || ""
  );
  return { name, displayName, aliases: normalizeAliases(raw), baseUrl, apiKey };
}

function normalizeInstances(config) {
  const rawInstances = config.instances || {};
  const instances = {};
  if (rawInstances && typeof rawInstances === "object" && !Array.isArray(rawInstances)) {
    for (const [key, raw] of Object.entries(rawInstances)) {
      const item = normalizeInstance(raw, key);
      instances[item.name] = item;
    }
  } else if (Array.isArray(rawInstances)) {
    for (const raw of rawInstances) {
      const item = normalizeInstance(raw);
      instances[item.name] = item;
    }
  } else {
    throw new Error("instances 必须是 object 或 array");
  }
  return instances;
}

function configDefaultName(config) {
  return pickFirst(config, ["default", "defaultInstance", "default_instance"]);
}

function findInstance(instances, selectedName) {
  if (selectedName in instances) return { instance: instances[selectedName], name: selectedName };
  for (const [name, instance] of Object.entries(instances)) {
    const candidates = [instance.displayName, ...(instance.aliases || [])];
    if (candidates.includes(selectedName)) return { instance, name };
  }
  return { instance: null, name: selectedName };
}

function resolveSettings() {
  const envBaseUrl = (process.env.OUTLINE_BASE_URL || "").replace(/\/$/, "");
  const envApiKey = process.env.OUTLINE_API_KEY || "";
  let config = {};
  let configPath = null;
  let instances = {};
  let configError = null;
  try {
    const loaded = loadInstanceConfig();
    config = loaded.config;
    configPath = loaded.configPath;
    instances = normalizeInstances(config);
  } catch (e) {
    configError = `读取 Outline 多实例配置失败：${e?.message || e}`;
  }

  const defaultInput = String(
    process.env.OUTLINE_INSTANCE_NAME
    || configDefaultName(config)
    || "default"
  ).trim();
  const { name: defaultName } = findInstance(instances, defaultInput);
  let selectedInput = String(process.env.OUTLINE_INSTANCE || defaultName).trim();
  if ((selectedInput === "default" || selectedInput === "env") && !(selectedInput in instances)) {
    selectedInput = defaultName;
  }

  const found = findInstance(instances, selectedInput);
  const instance = found.instance;
  const selectedName = found.name;
  const isDefault = selectedName === defaultName;
  let baseUrl = "";
  let apiKey = "";
  if (instance) {
    if (isDefault) {
      baseUrl = envBaseUrl || instance.baseUrl;
      apiKey = envApiKey || instance.apiKey;
    } else {
      baseUrl = instance.baseUrl;
      apiKey = instance.apiKey;
    }
  } else if (isDefault) {
    baseUrl = envBaseUrl;
    apiKey = envApiKey;
  }

  let instanceError = null;
  if (!instance && !isDefault) {
    instanceError = `未找到 Outline 实例：${selectedInput}。请在 .outline.instances.json 的 instances 中配置该名称，或使用实例的 name / displayName / aliases。`;
  } else if (instance && !isDefault && (!baseUrl || !apiKey)) {
    const missing = [];
    if (!baseUrl) missing.push("baseUrl");
    if (!apiKey) missing.push("apiKey");
    instanceError = `Outline 实例 ${selectedName} 缺少 ${missing.join(", ")}。`;
  }

  const currentInstance = {
    name: selectedName,
    displayName: instance?.displayName || selectedName,
    default: isDefault,
    configPath,
  };
  if (selectedInput !== selectedName) currentInstance.requested = selectedInput;

  return {
    baseUrl,
    apiKey,
    currentInstance,
    configError: configError || instanceError,
  };
}

loadEnv();

const SETTINGS = resolveSettings();
export const BASE_URL = SETTINGS.baseUrl;
export const API_KEY = SETTINGS.apiKey;
export const CURRENT_INSTANCE = SETTINGS.currentInstance;
export const INSTANCE_NAME = CURRENT_INSTANCE.name;
export const CONFIG_ERROR = SETTINGS.configError;

const DEFAULT_TIMEOUT_MS = 30_000;
const MAX_RETRIES = 3;

const HINTS = {
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
};

function ensureReady() {
  if (CONFIG_ERROR) {
    console.log(JSON.stringify({
      ok: false,
      error: CONFIG_ERROR,
    }));
    process.exit(1);
  }
  if (!BASE_URL || !API_KEY) {
    const homeEnv = path.join(os.homedir(), ".outline.env");
    const msg = `未找到环境配置。系统已优先检查过用户目录 (${homeEnv})，并依次查找了当前执行目录及 Skill 目录，但均未发现 .outline.env 或 .env 文件。\n请在用户目录下创建 .outline.env，并填入 OUTLINE_BASE_URL 和 OUTLINE_API_KEY 作为默认实例；多实例可在 .outline.instances.json 中配置，并用 OUTLINE_INSTANCE 或 --instance 选择。`;
    console.log(JSON.stringify({
      ok: false,
      error: msg,
    }));
    process.exit(1);
  }
  if (typeof fetch !== "function") {
    console.log(JSON.stringify({
      ok: false,
      error: "当前 Node 版本不支持全局 fetch（需要 Node >= 18）。",
    }));
    process.exit(1);
  }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export async function apiPost(endpoint, payload = {}) {
  ensureReady();
  const url = `${BASE_URL}/api/${endpoint}`;

  for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
    let res;
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);
      try {
        res = await fetch(url, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${API_KEY}`,
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify(payload),
          signal: controller.signal,
          redirect: "follow",
        });
      } finally {
        clearTimeout(timer);
      }
    } catch (e) {
      if (attempt < MAX_RETRIES - 1) {
        await sleep(1500 * (attempt + 1));
        continue;
      }
      return {
        ok: false, status: 0, endpoint,
        hint: "网络错误，已重试多次仍失败。",
        error: String(e?.message || e),
      };
    }

    if (res.status === 429 || (res.status >= 500 && res.status < 600)) {
      if (attempt < MAX_RETRIES - 1) {
        const retryAfter = res.headers.get("retry-after");
        const waitMs = retryAfter
          ? parseFloat(retryAfter) * 1000
          : Math.pow(2, attempt) * 1000;
        await sleep(waitMs);
        continue;
      }
    }

    let data;
    try { data = await res.json(); }
    catch { data = { text: await res.text() }; }

    if (res.status >= 400) {
      return {
        ok: false,
        status: res.status,
        endpoint,
        hint: HINTS[res.status] || "",
        raw: data,
      };
    }
    return data;
  }
  return { ok: false, endpoint, hint: "重试用尽。" };
}

// ---- pagination helper -----------------------------------------------------
export async function paginateAll(endpoint, payload = {}, { pageSize = 100, maxItems = null } = {}) {
  const body = { ...payload };
  const limit = Number(body.limit ?? pageSize);
  body.limit = limit;
  let offset = Number(body.offset ?? 0);
  const items = [];
  while (true) {
    body.offset = offset;
    body.limit = limit;
    const res = await apiPost(endpoint, body);
    if (res && res.ok === false) return res;
    const batch = res && Array.isArray(res.data) ? res.data : null;
    if (batch === null) return res;
    items.push(...batch);
    if (batch.length < limit) break;
    if (maxItems !== null && items.length >= maxItems) { items.length = maxItems; break; }
    offset += limit;
  }
  return { ok: true, data: items, count: items.length, paginated: true };
}

// ---- ID extraction ---------------------------------------------------------
const URL_DOC_RE = /\/doc(?:ument)?\/(?:.*?-)?([A-Za-z0-9]{10,})/i;
const URL_COLL_RE = /\/collection(?:s)?\/(?:.*?-)?([A-Za-z0-9-]{8,})/i;

export function extractId(value, kind = "doc") {
  if (!value) return value;
  const s = String(value).trim();
  if (!s.includes("://") && !s.includes("/")) return s;
  const re = kind === "doc" ? URL_DOC_RE : URL_COLL_RE;
  const m = s.match(re);
  if (m) return m[1];
  let tail = s.replace(/\/+$/, "").split("/").pop() || s;
  if (tail.includes("-")) tail = tail.split("-").pop();
  return tail;
}
