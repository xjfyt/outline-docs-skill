// user — read team members (for @mentions, permissions, etc.).
import { apiPost, paginateAll } from "./api.mjs";
import { renderResponse, printJson } from "./utils.mjs";

const FILTERS = new Set(["active", "admins", "members", "suspended", "invited", "all"]);

function summUser(u) {
  if (!u || typeof u !== "object") return u;
  return {
    id: u.id,
    name: u.name,
    email: u.email,
    role: u.role,
    isSuspended: u.isSuspended,
    lastActiveAt: u.lastActiveAt,
  };
}

export async function handleUser(action, f) {
  switch (action) {
    case "list": {
      const p = {};
      if (f.limit) p.limit = parseInt(f.limit, 10);
      if (f.offset) p.offset = parseInt(f.offset, 10);
      if (f.query) p.query = f.query;
      if (f.filter) {
        if (!FILTERS.has(f.filter)) {
          printJson({ ok: false, error: `--filter 需为：${[...FILTERS].join(", ")}` });
          process.exit(1);
        }
        p.filter = f.filter;
      }
      const res = f.all ? await paginateAll("users.list", p) : await apiPost("users.list", p);
      renderResponse(res, summUser, f.full, f);
      return;
    }
    case "info": {
      if (!f.id) { printJson({ ok: false, error: "需要 --id" }); process.exit(1); }
      renderResponse(await apiPost("users.info", { id: f.id }), summUser, f.full, f);
      return;
    }
    default:
      printJson({ ok: false, error: `未知 user 动作：${action}（可用：list, info）` });
      process.exit(2);
  }
}
