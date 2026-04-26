---
name: outline-docs-skill
description: 全面管理 Outline 知识库。当用户要求查看 / 搜索 / 创建 / 修改 / 增量编辑 / 归档 / 移动 / 复制 / 删除 / 发布 / 取消发布 / 导出 Outline 文档与文档集（Collection），上传图片，按本地目录递归批量上传，按 URL 编辑文档，按预置模板（如接口文档）撰写文档，管理公开分享链接 / 评论 / 历史版本 / 成员 / 置顶，或直连 Outline 任意 API 端点时，调用此 Skill。
---

# Outline 高级文档管理助手

跨平台 CLI，完整对接 Outline API。两套等价实现（Python httpx / Node.js 内置 fetch），统一入口自动选择。

## 0. 调用方式（必看）

**环境变量**：`OUTLINE_BASE_URL`、`OUTLINE_API_KEY`（必需）定义默认 Outline 实例。程序会优先在用户家目录下查找 `.outline.env` / `.env`，若没有再去依次检查当前运行目录及 skill 目录。若全未发现配置，则会提醒用户。配置项亦可直接用 export 呈现；仓库根有 `.outline.env.example` 可供参考。

**多实例**：可用 `.outline.instances.json` 给默认实例命名并配置其它 Outline。默认实例仍使用 `OUTLINE_BASE_URL` / `OUTLINE_API_KEY`；其它实例在 `instances` 内配置 `baseUrl` / `apiKey`。选择实例用 `--instance <name>`（可放命令任意位置）或 `OUTLINE_INSTANCE=<name>`，`<name>` 可是配置 key、`displayName` 或 `aliases`。若用户明确指定某个 Outline 实例 / 文档平台名，后续命令必须带上对应 `--instance`。

**统一入口**：

| 平台 | 命令 |
|---|---|
| macOS / Linux | `bash bin/run.sh <resource> <action> [...flags]` |
| Windows PowerShell | `bin\run.ps1 <resource> <action> [...flags]` |
| Windows cmd | `bin\run.cmd <resource> <action> [...flags]` |

入口按顺序解析运行时：`python3+httpx` → `python+httpx` → `uv`（临时注入 httpx）→ `node>=18`。缓存永不落入 skill 目录。

**首次使用先跑**：`bash bin/run.sh auth info`。

## 1. 核心规则（AI 必读）

| 规则 | 说明 |
|---|---|
| **接受 URL 也接受 ID** | 所有 `--id` / `--collection-id` / `--parent-document-id` 自动解析 Outline URL，无需手动抠 ID。 |
| **多实例必须显式选择** | 默认走环境变量里的默认实例；用户提到某个实例名、平台名、`displayName` 或别名时，在命令中加 `--instance "<用户提到的名称>"`，避免误写到默认实例。 |
| **默认输出"摘要"** | `list` / `view` / `search` 默认仅返回 `id/title/url/updatedAt/textPreview`。需要完整 JSON 时才加 `--full`。 |
| **改文档优先增量** | 短改动用 `--mode patch`（替换片段），追加用 `--mode append`，**只有大幅改写才整篇 `replace`**。 |
| **长内容走文件并清理** | 用 `--text-file xx.md` 而不是 `--text "..."`。务必加上 `--clean-file` 标志，使 Skill 在成功上传后自动删除本地缓存文件。 |
| **编写文档前先探查结构** | 如果用户提供链接要求在该处进行文档编写，**必须**先使用 `collection tree` 或 `document view` 等命令探查该链接处的目录树结构，搞清其**上下最少两层**的父子文档上下文。理清“当前位置在哪里、上下文中有些什么文档”后，再根据实际项目情况进行编写。 |
| **API 文档与模块组织结构** | 一般情况下遵循**“一个接口一文档”**的粒度。如果多个接口同属一个模块，则**必须先建立该模块的“主文档”**，在其中说明该模块的大致功能、调用流程（及模块间的联系等），然后再在模块主文档之下（作为其子文档）逐一创建具体的接口文档，以此类推。 |
| **开始写文档前必须先找模板** | **重点强调**：在编写任何文档之前，**必须先确定文档类型**，然后去查找对应的模板（参考 \`template list\`）。**只有在实在找不到合适模板的情况下，才可以自由发挥**。例如写接口文档：\`template show --name api-endpoint --body-only\` → 撰写 → \`document create\` → \`template lint\` 自检。 |
| **摘要长度可调** | 所有 `list/search/view` 支持 `--preview-len N`（0 = 只要标题+ID，不要正文预览，最省 token）。 |
| **列表翻页用 `--all`** | `document list/search`、`collection documents`、`user list` 均支持 `--all`，自动翻页累积。 |
| **报错读 hint 字段** | 错误 JSON 含 `hint` 中文提示，据此处理，不要盲目重试。 |
| **未覆盖端点走 `api call`** | Outline 端点很多（stars/fileOperations/groups…），本 skill 没封装的直接 `api call --endpoint X --data '{...}'`。 |
| **本地模板 ≠ 服务端模板** | 本 skill 的 `template` 子命令是**本地 markdown 写作模板**；Outline 服务端的"模板文档"要通过 `document create --template-id <服务端文档 ID>` 使用。 |
| **文档排序注意逆序** | Outline 默认把最新建的文档放在同级最上方。如果要排版序列（如一、二、三），请**逆序创建**（先建三再建二，最后建一）。对于已混乱的层级，可使用 `collection reorder --id <coll> [--parent-document-id X] --sort-by title` 一键按标题排序。 |
| **保持留白需插入占位符** | Outline 导入 Markdown 会吞并多余的自然空行。若要在各标题/模块间强制保留视觉空距，请不要单靠换行符，务必显式插入 `&nbsp;` 作为空行占位（注意前后换行），以确保渲染出等宽行距。 |

## 2. 命令决策表（按场景选命令）

| 用户意图 | 命令 |
|---|---|
| "看一下我有哪些集合" | `collection list` |
| "看 X 集合下的文档" | `collection documents --id <coll>`（平铺）/ `collection tree --id <coll>`（树形） |
| "将集合或某篇文档下的所有子文档批量排序" | `collection reorder --id <coll> [--parent-document-id <doc>] --sort-by title [--direction ASC/DESC]` |
| "找标题含 xxx 的文档" | `document find --query "xxx" [--collection-id ...]` |
| "全文搜 xxx" | `document search --query "xxx" [--titles-only]` |
| "看这篇文档内容"（只要正文） | `document view --id <id-or-url> --text-only` |
| "新建一篇文档" | `document create --collection-id ... --title ... --text-file body.md` |
| "加到文档末尾" | `document update --id <url> --mode append --text "..."` |
| "把 foo 改成 bar" | `document update --id <url> --mode patch --find "foo" --replace "bar"` |
| "整篇替换" | `document update --id <url> --mode replace --text-file new.md` |
| 归档/恢复/取消发布/复制/移动 | `document archive`/`restore`/`unpublish`/`duplicate`/`move` |
| "彻底删除" | `document delete --id ... --permanent` |
| "导出为 markdown" | `document export --id <url> --output out.md` |
| "看草稿 / 已归档" | `document drafts` / `document archived` |
| "上传一张图" | `upload --filepath ./a.png --document-id <url>` |
| "整个目录批量上传" | `upload_dir --dir ./docs --collection-id <coll> [--dry-run]` |
| "按接口模板写文档" | `template show --name api-endpoint --body-only` → 撰写 → `document create` → `template lint` |
| "给某篇文档生成公开分享链接" | `share create --document-id <url> --published` |
| "在某文档下发条评论 / 回复" | `comment create --document-id <url> --text "..." [--parent-comment-id ...]` |
| "看某文档的历史版本" | `revision list --document-id <url>` |
| "查团队成员 / 拿 user ID" | `user list --query "name"` |
| "把某文档置顶到集合或主页" | `pin create --document-id <url> [--collection-id <coll>]` |
| "调用本 skill 没封装的 Outline 端点" | `api call --endpoint <name> --data '{...}'` |

## 3. 需要更多细节时（按需 Read）

本 SKILL.md 只放 AI 决策所需的最少信息。具体用法请按需读取：

- **完整命令参数** → Read [`docs/commands.md`](docs/commands.md)
- **典型工作流 + Token 节省技巧** → Read [`docs/workflows.md`](docs/workflows.md)
- **错误排查 / 输出约定 / 注意事项 / 环境变量** → Read [`docs/troubleshooting.md`](docs/troubleshooting.md)

## 4. 目录结构（简要）

```
outline-docs-skill/
├── SKILL.md              # 本文件（精简版，决策所需的最少信息）
├── docs/                 # 详细文档（按需 Read）
├── bin/                  # run.sh / run.cmd / run.ps1 跨平台入口
├── python/               # Python 实现（httpx）
├── node/                 # Node.js 实现（零依赖，内置 fetch）
└── templates/            # 文档模板 + meta
```
