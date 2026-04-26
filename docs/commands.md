# 命令完整参考

> 所有示例统一使用 `bash bin/run.sh ...`；
> Windows cmd 换成 `bin\run.cmd ...`，PowerShell 换成 `bin\run.ps1 ...`，参数完全一致。

## 全局实例选择

默认实例继续来自 `OUTLINE_BASE_URL` / `OUTLINE_API_KEY`。其它实例在 `.outline.instances.json` 中配置后，可用以下任一方式选择：

```bash
bash bin/run.sh --instance family auth info
bash bin/run.sh document list --instance "家庭文档管理平台"
OUTLINE_INSTANCE=咪鼠 bash bin/run.sh collection list
bash bin/run.sh auth instances
```

`--instance` / `OUTLINE_INSTANCE` 可使用配置 key、`displayName` 或 `aliases`。

`.outline.instances.json` 顶层可设置 `dangerousOperationProtection: true`。默认关闭；开启后，整篇替换正文、永久删除、非 dry-run 批量上传需要额外添加 `--confirm` 或 `--confirm-dangerous`。

## auth — 健康检查

```bash
bash bin/run.sh auth info       # 当前工作区与 user
bash bin/run.sh auth config     # 完整 auth 配置
bash bin/run.sh auth instances  # 本地实例配置概览（不联网，不输出完整 API key）
```

## collection — 文档集

```bash
bash bin/run.sh collection list [--limit 25] [--full]
bash bin/run.sh collection view --id <id|url> [--full]
bash bin/run.sh collection create --name "..." [--description "..."] [--private]
bash bin/run.sh collection update --id <id|url> [--name ...] [--description ...]
bash bin/run.sh collection delete --id <id|url>
bash bin/run.sh collection tree --id <id|url>          # 树形结构
bash bin/run.sh collection documents --id <id|url>     # 平铺文档列表
```

## document — 文档（核心）

```bash
# 列表 / 查看
bash bin/run.sh document list [--collection-id ...] [--parent-document-id ...] \
       [--limit N] [--offset N] [--sort updatedAt|createdAt|title] [--direction ASC|DESC] [--full]
bash bin/run.sh document view --id <id|url> [--text-only] [--full]
bash bin/run.sh document drafts
bash bin/run.sh document archived

# 搜索 / 查找
bash bin/run.sh document search --query "..." [--titles-only] [--collection-id ...] \
       [--status-filter draft,archived,published] [--limit N]
bash bin/run.sh document find --query "标题关键词" [--collection-id ...] [--limit 5]

# 创建
bash bin/run.sh document create --collection-id <id|url> --title "..." \
       (--text "..." | --text-file body.md) \
       [--parent-document-id ...] [--icon ...] [--draft] [--template-id ...]
#   --template-id：Outline **服务端**模板的文档 ID（不是本 skill 的 `template` 子命令）。
#   本 skill 的 template 是**本地 markdown 写作模板**，见下文 § template。

# 更新（三种模式 — 短改动用 patch，追加用 append，大改才 replace）
bash bin/run.sh document update --id <id|url> --mode patch \
       --find "原文片段" --replace "新内容"
bash bin/run.sh document update --id <id|url> --mode append --text "追加段落"
bash bin/run.sh document update --id <id|url> --mode replace [--title ...] --text-file new.md
bash bin/run.sh document update --id <id|url> --publish    # 草稿转发布
bash bin/run.sh document update --id <id|url> --done       # 标记完成
# 若 dangerousOperationProtection=true，replace 正文需额外加 --confirm。

# 生命周期
bash bin/run.sh document archive    --id <id|url>
bash bin/run.sh document restore    --id <id|url> [--collection-id ...]
bash bin/run.sh document unpublish  --id <id|url>
bash bin/run.sh document duplicate  --id <id|url> [--title ...] [--collection-id ...] [--parent-document-id ...]
bash bin/run.sh document move       --id <id|url> [--collection-id ...] [--parent-document-id ...]
bash bin/run.sh document delete     --id <id|url> [--permanent]
# 若 dangerousOperationProtection=true，--permanent 需额外加 --confirm。

# 导出
bash bin/run.sh document export --id <id|url> [--output out.md]
```

## upload — 单图上传

```bash
bash bin/run.sh upload --filepath ./image.png --document-id <id|url>
# 输出含 markdown 行：![image.png](/api/attachments.redirect?id=...)，可拼到正文
```

## upload_dir — 整目录递归上传

```bash
bash bin/run.sh upload_dir --dir ./docs --collection-id <id|url> \
       [--dry-run] [--delay 1.0] [--ignore "*.tmp" --ignore "draft_*"]
# 若 dangerousOperationProtection=true，非 dry-run 上传需额外加 --confirm。
```

行为：
- 子目录 → 自动建一个父文档；如目录下有 `README.md` / `_index.md` / `index.md`，其内容作为父文档正文（否则用占位"目录索引页"）。
- markdown 文件首部 YAML frontmatter（`--- title: ... ---`）会被解析为标题。
- 文件中本地图片（`![](./img.png)`、`<img src="...">`）自动上传到对应文档并替换链接。
- 默认忽略隐藏文件、`node_modules`、`.git`、`.DS_Store` 等。
- `--dry-run` 仅打印将创建的文档，不写入 Outline —— **大目录前务必先跑一次 dry-run**。

## template — 文档模板系统（本 skill 内置的 markdown 写作模板）

> 这里的 `template` 是**本地 markdown 写作模板**：由 AI 读取 → 按约定格式写本地 .md → 再 `document create` 上传。
> Outline 服务端自有的"模板文档"则通过 `document create --template-id <服务端模板文档 ID>` 使用，二者不同。

```bash
bash bin/run.sh template list                                  # 列出所有模板
bash bin/run.sh template show --name api-endpoint              # 含 meta + body
bash bin/run.sh template show --name api-endpoint --body-only  # 仅模板正文，更省 token
bash bin/run.sh template lint --name api-endpoint --file my.md # 校验本地稿件是否符合模板
```

**模板存放**：默认在 `outline-docs-skill/templates/`。可设 `OUTLINE_TEMPLATES_DIR` 指向自定义目录（同名优先于内置）。

**当前内置模板**：

| name | 用途 |
|---|---|
| `api-endpoint` | HTTP 接口文档（一级标题 `# 一、xxx`、二级 `## **1、xxx**`、三级 `### （1）xxx`，块间留空行） |

新增模板：在 `templates/` 放 `<name>.md` + `<name>.meta.json`，参考 `api-endpoint` 写 meta。

## share — 公开分享链接

```bash
bash bin/run.sh share list [--document-id <id|url>] [--limit N]
bash bin/run.sh share info (--id <share-id> | --document-id <id|url>)
bash bin/run.sh share create --document-id <id|url> [--published] [--include-children]
bash bin/run.sh share update --id <share-id> [--published] [--include-children]
bash bin/run.sh share revoke --id <share-id>
```

`share` 是给外部用户看的只读公开链接，不同于协作者邀请；`--include-children` 允许访问子文档树。

## comment — 文档评论

```bash
bash bin/run.sh comment list --document-id <id|url> [--limit N]
bash bin/run.sh comment info --id <comment-id>
bash bin/run.sh comment create --document-id <id|url> --text "..." [--parent-comment-id <id>]
bash bin/run.sh comment update --id <comment-id> --text "..."
bash bin/run.sh comment delete --id <comment-id>
```

`--text` 传纯文本，CLI 会自动包装为 Outline 需要的 ProseMirror 结构；回复评论传 `--parent-comment-id`。

## revision — 文档历史版本（只读）

```bash
bash bin/run.sh revision list --document-id <id|url> [--limit N]
bash bin/run.sh revision info --id <revision-id> [--full]
```

用于追溯文档历次修改；`--full` 才返回正文全文。

## user — 团队成员

```bash
bash bin/run.sh user list [--query "name"] [--filter active|admins|members|suspended|invited|all] [--limit N] [--all]
bash bin/run.sh user info --id <user-id>
```

用于查 @mention 对象、分配协作权限时的 user ID。

## pin — 置顶文档

```bash
bash bin/run.sh pin list [--collection-id <id|url>]    # 不传 collection-id = 工作区主页的 pin
bash bin/run.sh pin create --document-id <id|url> [--collection-id <id|url>] [--index N]
bash bin/run.sh pin delete --id <pin-id>
```

## api — 通用 API 逃生口（未封装的端点）

```bash
bash bin/run.sh api call --endpoint stars.list
bash bin/run.sh api call --endpoint documents.info --data '{"id":"doc-abc"}'
bash bin/run.sh api call --endpoint fileOperations.list --data-file payload.json
bash bin/run.sh api call --endpoint groups.list --all       # data 是数组时自动翻页
```

所有端点走同一个 POST；payload 用 `--data '{...}'` 或 `--data-file path.json`。
Outline 端点完整清单见 https://www.getoutline.com/developers 。
