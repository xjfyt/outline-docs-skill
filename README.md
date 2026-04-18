# outline-docs-skill

一个跨平台的 [Claude Code](https://docs.claude.com/en/docs/claude-code) **Skill**，让 Claude 能精准、省 token 地管理 [Outline](https://www.getoutline.com/) 知识库。

> 这是 Skill 的**源码仓库**。`SKILL.md` 是 Claude 读取的入口，`README.md` 只给仓库浏览者看（下载 Skill 压缩包时会被自动排除）。

---

## 功能

两套等价实现（Python httpx / Node.js 内置 fetch），统一入口按优先级自动选择可用运行时：`python3+httpx` → `python+httpx` → `uv`（临时注入 httpx）→ `node>=18`。

| 资源 | 能力 |
|---|---|
| `auth` | 健康检查、显示当前工作区 / 用户 / 运行时 / skill 版本 |
| `collection` | 文档集：list / view / create / update / delete / tree / documents |
| `document` | 核心：list / view / create / update / delete / move / search / find / archive / restore / unpublish / duplicate / export / drafts / archived |
| `upload` | 单图上传（附件） |
| `upload_dir` | 整目录递归上传（自动识别 README/_index、YAML frontmatter、本地图片并同步上传） |
| `template` | **本地 markdown 写作模板** list / show / lint（如 HTTP 接口文档模板）|
| `share` | 公开分享链接 list / info / create / update / revoke |
| `comment` | 评论 list / info / create / update / delete（自动包装为 ProseMirror 结构） |
| `revision` | 文档历史版本 list / info（只读） |
| `user` | 团队成员 list / info |
| `pin` | 置顶 list / create / delete |
| `api` | 通用 POST 端点逃生口，覆盖未封装的 Outline API（stars/fileOperations/groups…） |

关键特性：

- **URL 即 ID**：所有 `--id` / `--collection-id` / `--parent-document-id` 自动解析 Outline URL。
- **摘要优先**：list/search/view 默认返回摘要（省 token）；`--full` 拿完整响应；`--preview-len N` 控制正文预览长度，`0` 直接不要预览。
- **自动翻页**：`document list/search`、`collection documents`、`user list`、`api call` 均支持 `--all`。
- **增量改文档**：短改动用 `--mode patch --find "原文" --replace "新内容"`，追加用 `--mode append`，大改才 `replace`。
- **中文 hint**：错误返回含 `hint` 中文提示（覆盖 400/401/403/404/422/429/5xx + 网络错误）。
- **缓存隔离**：Python 的 `__pycache__`、uv 的 `.venv`、Node 依赖等**永远不会**落到 Skill 目录内，默认放 `$OUTLINE_CACHE_DIR`。

---

## 安装

### 方式一：作为 Claude Code Skill 使用

把整个 Skill 目录放到 Claude Code 会扫描的 skills 路径（或项目内 `.claude/skills/` 下）：

**macOS / Linux**
```bash
git clone https://github.com/<your-name>/outline-docs-skill.git ~/.claude/skills/outline-docs-skill
```

**Windows PowerShell**
```powershell
git clone https://github.com/<your-name>/outline-docs-skill.git "$env:USERPROFILE\.claude\skills\outline-docs-skill"
```

之后在 Claude Code 会话里提到 Outline 相关需求，Claude 会自动匹配并使用本 Skill。

### 方式二：仅作为命令行工具使用

直接克隆到任意位置，按下面"手动调用"里的方式敲命令即可。

### 方式三：下载 ZIP 包（纯净 Skill，无 README）

在 GitHub 上点 **Code → Download ZIP**，或：

```bash
git archive --format=zip --output=outline-docs-skill.zip HEAD
```

由于 `.gitattributes` 配置了 `export-ignore`，下载得到的压缩包**不含** `README.md`、`.gitignore`、`.gitattributes`、`LICENSE`、`.github/` 等仓库元文件。

---

## 配置

两个必需环境变量：

| 变量 | 说明 |
|---|---|
| `OUTLINE_BASE_URL` | Outline 站点地址，如 `https://docs.example.com`（不要带尾部斜杠） |
| `OUTLINE_API_KEY`  | 在 Outline 「设置 → API Tokens」里生成 |

支持的配置位置（按优先级从高到低）：

1. 进程环境变量（`export` / `set` / `$env:`）
2. 当前工作目录 `<cwd>/outline.env` 或 `<cwd>/.env`（项目级覆盖）
3. **Skill 目录 `<skill>/outline.env` 或 `<skill>/.env`**（本仓库根目录；推荐放这里，跟着 skill 一起管理）
4. 用户家目录 `~/outline.env` 或 `~/.env`

仓库根已提供 [`outline.env.example`](outline.env.example) 作为配置模板，复制并改名即可：

```bash
cp outline.env.example outline.env
# 然后编辑 outline.env，填入真实的 BASE_URL 和 API_KEY
```

> `outline.env` 与 `.env` 已加入 [`.gitignore`](.gitignore)，不会被误提交；`outline.env.example` 才会进仓库。

可选环境变量：

| 变量 | 作用 | 默认 |
|---|---|---|
| `OUTLINE_RUN_VIA` | 强制指定运行时：`python3` / `python` / `uv` / `node` | 自动探测 |
| `OUTLINE_CACHE_DIR` | uv / pycache 的根目录 | `$XDG_CACHE_HOME/outline-skill`（Unix）/ `%LOCALAPPDATA%\outline-skill`（Win） |
| `OUTLINE_PIP_MIRROR` | 报错提示里推荐的 pip 镜像 | 清华镜像 |
| `OUTLINE_TEMPLATES_DIR` | 自定义本地模板目录（与内置并存；同名优先） | 无 |

---

## 快速上手

首次使用先跑健康检查：

```bash
bash bin/run.sh auth info
```

成功响应大致长这样（含运行时与 skill 版本）：

```json
{
  "ok": true,
  "baseUrl": "https://docs.example.com",
  "skillVersion": "1.1.0",
  "runtime": { "lang": "python", "python": "3.12.4", "httpx": "0.27.0", "runVia": "auto", "platform": "darwin" },
  "user": { "id": "...", "name": "...", "email": "...", "role": "admin" },
  "team": { "id": "...", "name": "...", "url": "..." }
}
```

### 常用命令（给"看 README 的人"而不是 Claude 本身）

```bash
# 列出所有集合（摘要）
bash bin/run.sh collection list

# 按标题找文档
bash bin/run.sh document find --query "接口" --collection-id <coll-url>

# 按 URL 增量改文档
bash bin/run.sh document update --id "https://docs.example.com/doc/my-doc-Abc123" \
       --mode patch --find "code=10010" --replace "code=200"

# 递归上传本地目录到某集合（先 dry-run）
bash bin/run.sh upload_dir --dir ./docs --collection-id <coll-url> --dry-run

# 按内置模板写接口文档
bash bin/run.sh template show --name api-endpoint --body-only  # 看格式
# ... 写到 my_api.md ...
bash bin/run.sh template lint --name api-endpoint --file my_api.md
bash bin/run.sh document create --collection-id <coll-url> --title "xxx" --text-file my_api.md

# 调用本 skill 未封装的 Outline 端点
bash bin/run.sh api call --endpoint stars.list
bash bin/run.sh api call --endpoint fileOperations.list --all
```

Windows cmd 把 `bash bin/run.sh` 换成 `bin\run.cmd`，PowerShell 换成 `bin\run.ps1`，参数完全一致。

完整命令参考见 [`docs/commands.md`](docs/commands.md)。
典型工作流 + Token 节省技巧见 [`docs/workflows.md`](docs/workflows.md)。
错误排查见 [`docs/troubleshooting.md`](docs/troubleshooting.md)。

---

## 目录结构

```
outline-docs-skill/
├── SKILL.md              # Skill 入口（Claude 读取；必须在根部）
├── bin/                  # 跨平台统一入口：run.sh / run.cmd / run.ps1
├── docs/                 # 详细文档（命令参考 / 工作流 / 故障排查），SKILL.md 里按需 Read
├── python/               # Python 实现（httpx）
│   ├── outline_cli.py
│   └── scripts/*.py
├── node/                 # Node.js 实现（零依赖，内置 fetch，要求 Node >= 18）
│   ├── outline_cli.mjs
│   └── lib/*.mjs
├── templates/            # 本地 markdown 写作模板 + meta.json
├── outline.env.example   # 配置模板，复制为 outline.env 后填入真实值
├── README.md             # 本文件（仓库说明；export-ignore，不进 skill 包）
├── LICENSE               # MIT
├── .gitignore
└── .gitattributes
```

---

## 运行时要求

任一满足即可（入口会自动探测）：

- Python 3.8+ 且已装 `httpx`
- 装了 [uv](https://github.com/astral-sh/uv)（会临时注入 httpx，不污染全局）
- Node.js >= 18（内置 `fetch`，零依赖）

---

## 贡献

欢迎 PR：

1. Fork & clone
2. 本地跑 `bash bin/run.sh auth info` 确认环境 OK
3. 跑冒烟：`OUTLINE_RUN_VIA=node bash bin/run.sh template list` 与 `OUTLINE_RUN_VIA=uv bash bin/run.sh template list`
4. 新增资源时，Python (`python/scripts/`) 与 Node (`node/lib/`) 两端等价实现，并在两个 `outline_cli.*` 里注册
5. 更新 `SKILL.md` 决策表 + `docs/commands.md`

---

## 许可证

MIT —— 详见 [LICENSE](LICENSE)。
