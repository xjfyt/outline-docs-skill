import { apiPost, extractId, paginateAll } from "./api.mjs";
import { renderResponse, summarizeCollection, summarizeDoc, printJson } from "./utils.mjs";

function walkTree(nodes, depth = 0, lines = []) {
  for (const n of nodes || []) {
    const title = n.title || "(无标题)";
    lines.push(`${"  ".repeat(depth)}- ${title}  [${n.id}]`);
    if (n.children?.length) walkTree(n.children, depth + 1, lines);
  }
  return lines;
}

export async function handleCollection(action, f) {
  switch (action) {
    case "list": {
      const p = {};
      if (f.limit) p.limit = parseInt(f.limit, 10);
      if (f.offset) p.offset = parseInt(f.offset, 10);
      renderResponse(await apiPost("collections.list", p), summarizeCollection, f.full, f);
      return;
    }
    case "view": {
      const res = await apiPost("collections.info", { id: extractId(f.id, "collection") });
      renderResponse(res, summarizeCollection, f.full, f);
      return;
    }
    case "create": {
      const p = { name: f.name };
      if (f.description) p.description = f.description;
      p.permission = f.private ? null : "read_write";
      renderResponse(await apiPost("collections.create", p), summarizeCollection, f.full, f);
      return;
    }
    case "update": {
      const p = { id: extractId(f.id, "collection") };
      if (f.name) p.name = f.name;
      if (f.description !== undefined) p.description = f.description;
      renderResponse(await apiPost("collections.update", p), summarizeCollection, f.full, f);
      return;
    }
    case "delete": {
      const res = await apiPost("collections.delete", { id: extractId(f.id, "collection") });
      renderResponse(res, null, true);
      return;
    }
    case "tree": {
      const res = await apiPost("collections.documents", { id: extractId(f.id, "collection") });
      if (res && res.ok === false) { printJson(res); process.exit(1); }
      const nodes = res.data ?? res;
      if (f.full) printJson(res);
      else console.log(walkTree(nodes).join("\n"));
      return;
    }
    case "reorder": {
      const cid = extractId(f.id, "collection");
      const res = await apiPost("collections.documents", { id: cid });
      if (res && res.ok === false) { printJson(res); process.exit(1); }
      const nodes = res.data ?? res;
      
      let targetNodes = null;
      let pid = f.parentDocumentId;
      if (pid) {
        pid = extractId(pid, "doc");
        const queue = [...nodes];
        while (queue.length > 0) {
          const curr = queue.shift();
          if (curr.id === pid) {
            targetNodes = curr.children || [];
            break;
          }
          if (curr.children) queue.push(...curr.children);
        }
      } else {
        targetNodes = nodes;
      }
      
      if (!targetNodes) {
        printJson({ ok: false, error: "未找到指定的 parent-document-id 或节点为空" });
        return;
      }
      if (targetNodes.length === 0) {
        printJson({ ok: true, msg: "目录下无子文档可排序" });
        return;
      }

      const sortBy = f.sortBy || "title";
      const rev = f.direction === "DESC" ? -1 : 1;
      
      targetNodes.sort((a, b) => {
        const valA = String(a[sortBy] || "");
        const valB = String(b[sortBy] || "");
        return valA.localeCompare(valB) * rev;
      });

      const moved = [];
      for (let i = 0; i < targetNodes.length; i++) {
        const n = targetNodes[i];
        const p = { id: n.id, collectionId: cid, index: i };
        if (pid) p.parentDocumentId = pid;
        await apiPost("documents.move", p);
        moved.push(n.title);
      }
      printJson({ ok: true, msg: `成功重排 ${moved.length} 篇文档`, order: moved });
      return;
    }
    case "documents": {
      const p = { collectionId: extractId(f.id, "collection") };
      if (f.limit) p.limit = parseInt(f.limit, 10);
      if (f.offset) p.offset = parseInt(f.offset, 10);
      const res = f.all ? await paginateAll("documents.list", p) : await apiPost("documents.list", p);
      renderResponse(res, summarizeDoc, f.full, f);
      return;
    }
    default:
      printJson({ ok: false, error: `未知 collection 动作：${action}` });
      process.exit(2);
  }
}
