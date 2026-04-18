import os from "node:os";
import { apiPost, BASE_URL } from "./api.mjs";
import { printJson } from "./utils.mjs";

const SKILL_VERSION = "1.1.0";

function runtimeInfo() {
  return {
    lang: "node",
    node: process.version,
    runVia: process.env.OUTLINE_RUN_VIA || "auto",
    platform: os.platform(),
  };
}

export async function handleAuth(action, _flags) {
  if (action === "info") {
    const res = await apiPost("auth.info");
    if (res && res.ok === false) { printJson(res); return; }
    const data = res.data || {};
    const user = data.user || {};
    const team = data.team || {};
    printJson({
      ok: true,
      baseUrl: BASE_URL,
      skillVersion: SKILL_VERSION,
      runtime: runtimeInfo(),
      user: { id: user.id, name: user.name, email: user.email, role: user.role },
      team: { id: team.id, name: team.name, url: team.url },
    });
  } else if (action === "config") {
    printJson(await apiPost("auth.config"));
  } else {
    printJson({ ok: false, error: "未知 auth 动作；可用：info, config" });
    process.exit(2);
  }
}
