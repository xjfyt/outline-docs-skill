# Outline 文档模板库

放置可复用的 Markdown 文档模板。每个模板由两个文件组成：

- `<name>.md`     —— 模板正文（直接展示给 AI 参考）
- `<name>.meta.json` —— 模板元数据（必需小节、可选小节、标题格式约束、给 AI 的写作指引）

## 现有模板

| 名称 | 适用场景 |
|---|---|
| `api-endpoint` | HTTP 接口文档（标准内/外部 API 说明） |

## 添加新模板

1. 复制一份 `api-endpoint.md` + `api-endpoint.meta.json`，按需修改。
2. `meta.json` 至少包含 `name`、`description`、`required_sections`、`heading_style`、`instructions_for_ai`。
3. 通过 `bash bin/run.sh template list`（macOS/Linux）或 `bin\run.cmd template list`（Windows）验证已被识别。

## 自定义模板目录

设置环境变量 `OUTLINE_TEMPLATES_DIR=/path/to/your/templates` 即可在内置模板基础上额外加载你自己的模板（同名时以自定义优先）。
