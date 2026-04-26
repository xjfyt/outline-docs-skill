#!/usr/bin/env node
import { parseArgs } from "./lib/argparse.mjs";
import { printJson } from "./lib/utils.mjs";

const HELP = `Outline API CLI (Node.js) —— 管理 Outline 知识库

用法：
  node outline_cli.mjs <resource> <action> [--flags]

资源：
  auth        info | config | instances
  collection  list | view | create | update | delete | tree | documents | reorder
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
  --instance X   选择 .outline.instances.json 中的 Outline 实例（也可用 OUTLINE_INSTANCE）
  --confirm      危险操作保护开启时，确认执行当前危险操作
  --full         输出完整响应（默认只返摘要）
  --preview-len  摘要中 textPreview 长度（0 = 不要 textPreview）
  --all          list/search 自动翻页累积全部结果
`;

function applyInstanceFlag(argv) {
  const cleaned = [];
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === "--instance" || arg === "--outline-instance") {
      const value = argv[i + 1];
      if (!value || value.startsWith("-")) {
        console.log(JSON.stringify({ ok: false, error: "--instance 需要实例名" }));
        process.exit(2);
      }
      process.env.OUTLINE_INSTANCE = value;
      i++;
      continue;
    }
    if (arg.startsWith("--instance=")) {
      process.env.OUTLINE_INSTANCE = arg.slice("--instance=".length);
      continue;
    }
    if (arg.startsWith("--outline-instance=")) {
      process.env.OUTLINE_INSTANCE = arg.slice("--outline-instance=".length);
      continue;
    }
    cleaned.push(arg);
  }
  return cleaned;
}

async function main() {
  const argv = applyInstanceFlag(process.argv.slice(2));
  if (argv.length === 0 || argv[0] === "-h" || argv[0] === "--help") {
    console.log(HELP);
    process.exit(argv.length === 0 ? 2 : 0);
  }
  const { resource, action, flags } = parseArgs(argv);
  try {
    switch (resource) {
      case "auth": {
        const { handleAuth } = await import("./lib/auth.mjs");
        return await handleAuth(action, flags);
      }
      case "collection": {
        const { handleCollection } = await import("./lib/collection.mjs");
        return await handleCollection(action, flags);
      }
      case "document": {
        const { handleDocument } = await import("./lib/document.mjs");
        return await handleDocument(action, flags);
      }
      case "upload": {
        const { handleUpload } = await import("./lib/attachment.mjs");
        return await handleUpload(action, flags);
      }
      case "upload_dir": {
        const { handleUploadDir } = await import("./lib/upload_dir.mjs");
        return await handleUploadDir(action, flags);
      }
      case "template": {
        const { handleTemplate } = await import("./lib/template.mjs");
        return await handleTemplate(action, flags);
      }
      case "share": {
        const { handleShare } = await import("./lib/share.mjs");
        return await handleShare(action, flags);
      }
      case "comment": {
        const { handleComment } = await import("./lib/comment.mjs");
        return await handleComment(action, flags);
      }
      case "revision": {
        const { handleRevision } = await import("./lib/revision.mjs");
        return await handleRevision(action, flags);
      }
      case "user": {
        const { handleUser } = await import("./lib/user.mjs");
        return await handleUser(action, flags);
      }
      case "pin": {
        const { handlePin } = await import("./lib/pin.mjs");
        return await handlePin(action, flags);
      }
      case "api": {
        const { handleApi } = await import("./lib/generic.mjs");
        return await handleApi(action, flags);
      }
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
