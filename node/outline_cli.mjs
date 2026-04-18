#!/usr/bin/env node
import { parseArgs } from "./lib/argparse.mjs";
import { handleAuth } from "./lib/auth.mjs";
import { handleCollection } from "./lib/collection.mjs";
import { handleDocument } from "./lib/document.mjs";
import { handleUpload } from "./lib/attachment.mjs";
import { handleUploadDir } from "./lib/upload_dir.mjs";
import { handleTemplate } from "./lib/template.mjs";
import { handleShare } from "./lib/share.mjs";
import { handleComment } from "./lib/comment.mjs";
import { handleRevision } from "./lib/revision.mjs";
import { handleUser } from "./lib/user.mjs";
import { handlePin } from "./lib/pin.mjs";
import { handleApi } from "./lib/generic.mjs";
import { printJson } from "./lib/utils.mjs";

const HELP = `Outline API CLI (Node.js) —— 管理 Outline 知识库

用法：
  node outline_cli.mjs <resource> <action> [--flags]

资源：
  auth        info | config
  collection  list | view | create | update | delete | tree | documents
  document    list | view | create | update | delete | move | search | find
              | archive | restore | unpublish | duplicate | export | drafts | archived
  upload      单图上传（需 --filepath --document-id）
  upload_dir  整目录递归上传（需 --dir --collection-id）
  template    list | show | lint   (本 skill 内置写作模板；不同于 Outline 服务端的 --template-id)
  share       list | info | create | update | revoke
  comment     list | info | create | update | delete
  revision    list | info        （只读：文档历史版本）
  user        list | info        （团队成员，用于 @mention / 权限）
  pin         list | create | delete
  api         call --endpoint X   （通用 POST 端点，覆盖未封装的 API）

通用标志：
  --full         输出完整响应（默认只返摘要）
  --preview-len  摘要中 textPreview 长度（0 = 不要 textPreview）
  --all          list/search 自动翻页累积全部结果
`;

async function main() {
  const argv = process.argv.slice(2);
  if (argv.length === 0 || argv[0] === "-h" || argv[0] === "--help") {
    console.log(HELP);
    process.exit(argv.length === 0 ? 2 : 0);
  }
  const { resource, action, flags } = parseArgs(argv);
  try {
    switch (resource) {
      case "auth":       return await handleAuth(action, flags);
      case "collection": return await handleCollection(action, flags);
      case "document":   return await handleDocument(action, flags);
      case "upload":     return await handleUpload(action, flags);
      case "upload_dir": return await handleUploadDir(action, flags);
      case "template":   return await handleTemplate(action, flags);
      case "share":      return await handleShare(action, flags);
      case "comment":    return await handleComment(action, flags);
      case "revision":   return await handleRevision(action, flags);
      case "user":       return await handleUser(action, flags);
      case "pin":        return await handlePin(action, flags);
      case "api":        return await handleApi(action, flags);
      default:
        printJson({
          ok: false,
          error: `未知 resource：${resource}`,
          available: ["auth", "collection", "document", "upload", "upload_dir", "template", "share", "comment", "revision", "user", "pin", "api"],
        });
        process.exit(2);
    }
  } catch (e) {
    printJson({ ok: false, error: String(e?.message || e), stack: e?.stack });
    process.exit(1);
  }
}

main();
