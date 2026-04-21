# 典型工作流 + Token 节省技巧

## 1. 写接口及模块文档（首选场景）

```bash
# 1) 探查现有文档结构（首要前提）
# 若用户发来所在文档链接，先用树形结构查看上下文至少两层层级
bash bin/run.sh collection tree --id <coll-url>

# 2) 建立模块主文档（若接口有对应的模块且尚未建档）
# 优先创建说明大概功能、调用流程的模块文档
bash bin/run.sh document create --collection-id <coll-url> --title "某某模块说明" --text-file module.md

# 3) 查阅接口文档模板格式 + 写作要点（编写接口前的第一步）
bash bin/run.sh template show --name api-endpoint

# 4) 按模板撰写对应接口文档到本地 my_api.md（一接口一文档）：
#    - 正文不要重复写文档标题名字
#    - 主干章节使用最高级 H1（#）+ 中文数字，例如：# 一、请求说明
#    - 二级使用 H2（##）+ 阿拉伯数字，例如：## 1、Header参数
#    - 三级使用 H3（###），例如：### (1) 说明
#    - 每个标题块之间空一行
#    - URL/方法/curl 用 ```bash，JSON 用 ```json
#    - 没用到的小节整段省略，但保留小节顺序与命名

# 5) 自检
bash bin/run.sh template lint --name api-endpoint --file my_api.md

# 6) 在模块主文档下创建子文档
bash bin/run.sh document create \
       --collection-id <api-doc-collection-url> \
       --parent-document-id <module-doc-id> \
       --title "8、新增数据源(具体接口)" --text-file my_api.md
```

## 2. 通过 URL 修改文档（增量改）

用户："请把 https://docs.xxx.com/doc/my-doc-Abc123 中的 `code=10010` 改成 `code=200`"。

```bash
bash bin/run.sh document update \
       --id "https://docs.xxx.com/doc/my-doc-Abc123" \
       --mode patch --find "code=10010" --replace "code=200"
```

## 3. 在文档末尾追加一节

```bash
bash bin/run.sh document update \
       --id "<doc-url>" --mode append \
       --text-file new_section.md
```

## 4. 整理一篇老文档（先看再大改）

```bash
bash bin/run.sh document view --id "<url>" --text-only > /tmp/cur.md
# AI 在 /tmp/cur.md 上修改 → 写到 /tmp/new.md
bash bin/run.sh document update --id "<url>" --mode replace --text-file /tmp/new.md
```

## 5. 把本地文档库迁移到 Outline

```bash
# 先 dry-run 看树形
bash bin/run.sh upload_dir --dir ./docs --collection-id <coll-url> --dry-run

# 确认后正式上传
bash bin/run.sh upload_dir --dir ./docs --collection-id <coll-url> --delay 1.5
```

## 6. 备份单篇文档到本地

```bash
bash bin/run.sh document export --id <url> --output backup.md
```

---

## Token 节省 / 效率提示

- **优先用摘要输出**：list/search 默认就是摘要；除非确实要正文/全部字段才加 `--full`。
- **正文用 `--text-only`**：`document view --text-only` 只输出 markdown 正文，不带其它元数据。
- **改动优先 patch**：避免把整篇文档塞回 `--text` 里。
- **模板用 `--body-only`**：拿模板时只看正文格式即可（meta 里的 instructions_for_ai 看一次就够）。
- **大目录用 `--dry-run`**：避免一次性误传几百篇。
- **错误带 hint 字段**：直接读 hint 定位问题，不要重复试。
