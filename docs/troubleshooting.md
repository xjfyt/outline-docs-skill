# 常见错误 / 故障排查

## 错误对照表

| 现象 | 原因 / 处理 |
|---|---|
| `status: 401` | API key 无效或未配置；检查 `.outline.env` 或 `OUTLINE_API_KEY`。 |
| `status: 403` | 当前 key 对该集合/文档无权限。 |
| `status: 404` | ID/URL 不对，或文档已删除/归档。归档的文档要先 `document restore`。 |
| `status: 429` | 限流。CLI 已自动重试 3 次；`upload_dir` 加大 `--delay`（如 2.0/3.0）。 |
| `Missing OUTLINE_BASE_URL or OUTLINE_API_KEY` | 配置默认实例环境变量；本 Skill 支持 `.outline.env`/`.env`。仓库根有 `.outline.env.example` 可复制。 |
| `未找到 Outline 实例` | `OUTLINE_INSTANCE` / `--instance` 指向的名称不在 `.outline.instances.json` 的 key、`displayName` 或 `aliases` 中。 |
| `Outline 实例选择器重复` | 多个实例使用了相同 key、`displayName` 或 `aliases`；重命名后再执行，避免误写实例。 |
| `Outline 实例 X 缺少 baseUrl/apiKey` | 非默认实例必须在 `.outline.instances.json` 中提供 `baseUrl` 和 `apiKey`，或用 `apiKeyEnv` 指向环境变量。 |
| `危险操作保护已开启` | `.outline.instances.json` 开启了 `dangerousOperationProtection`；确认操作后重跑并添加 `--confirm` 或 `--confirm-dangerous`。 |
| `未找到可用的运行时` | 装 uv（`curl -LsSf https://astral.sh/uv/install.sh \| sh`）、或 pip 装 httpx、或装 Node >= 18。 |
| Node 版本 < 18 | 全局 fetch 不可用；升级 Node 或改用 Python/uv 路径。 |

## 输出约定

- 成功响应：`{"ok": true, ...}` 或带 `data` 字段。
- 失败响应：`{"ok": false, "status": <http>, "outlineInstance": {...}, "hint": "...中文提示...", "raw": ...}`。
- 列表摘要：`{"ok": true, "count": N, "items": [...]}`。
- 本地实例概览：`auth instances` 不联网，只输出实例名、displayName、aliases、baseUrl 与 `hasApiKey`，不会输出完整 API key。
- 中文文本不会被转义为 `\uXXXX`。

## 注意事项

- 所有 `--text` / `--text-file` 内容请使用标准 Markdown。
- 默认创建的文档**直接发布**；要存草稿请加 `--draft`。
- `document delete` 默认进回收站，可恢复；`--permanent` 才永久删除。
- 修改的内容如果包含本地图片，**单文件场景**需手动走「先创建 / 用 upload 上传 / 用 patch 把图片 markdown 行追加进文档」三步；**目录场景**用 `upload_dir` 全自动。
- Skill 目录内**永远不会**出现 `.venv`、`__pycache__`、`node_modules`、`uv` 缓存；所有缓存都在 `$OUTLINE_CACHE_DIR`（默认位于用户缓存目录）。安全地频繁更新本 skill 不会打扰你的本地开发环境。

## 强制指定运行时

```bash
OUTLINE_RUN_VIA=node     bash bin/run.sh ...   # 前端开发者首选：走 Node 实现
OUTLINE_RUN_VIA=uv       bash bin/run.sh ...   # 无系统 Python 时，用 uv 临时注入
OUTLINE_RUN_VIA=python3  bash bin/run.sh ...
OUTLINE_RUN_VIA=python   bash bin/run.sh ...
```

Windows cmd：`set OUTLINE_RUN_VIA=node && bin\run.cmd ...`
Windows PowerShell：`$env:OUTLINE_RUN_VIA="node"; bin\run.ps1 ...`

## 其它可选环境变量

| 变量 | 作用 | 默认 |
|---|---|---|
| `OUTLINE_INSTANCE_NAME` | 默认实例名称 | `default` |
| `OUTLINE_INSTANCE` | 当前命令选择的实例名；等价于 `--instance` | 默认实例 |
| `OUTLINE_INSTANCES_FILE` | 多实例配置文件路径 | 自动查找 `.outline.instances.json` |
| `OUTLINE_PIP_MIRROR` | 失败提示中 pip install 推荐的镜像 | `https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple` |
| `OUTLINE_CACHE_DIR` | 存放 uv / pycache 的根目录 | `$XDG_CACHE_HOME/outline-skill`（Unix）/ `%LOCALAPPDATA%\outline-skill`（Win） |
| `OUTLINE_TEMPLATES_DIR` | 自定义模板目录（与内置并存；同名优先） | 无 |
