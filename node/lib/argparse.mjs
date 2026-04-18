// Minimal arg parser — mirrors Python argparse behaviour used by the skill.
//
// 解析规则（无需硬编码 bool 列表 —— 从参数形态自动判定）：
//   1. 第一个 token（不以 `-` 开头）是 resource。
//   2. 第二个 token 若不以 `-` 开头，视为 action；否则无 action。
//   3. 对每个 `--flag`：
//      - 下一个 token 不存在 / 以 `-` 开头 → 当前 flag 为布尔 true。
//      - 否则消费下一个 token 作为值。
//   4. 约定可多次出现的 flag（`--ignore`）累积为数组。
//   5. kebab-case 键自动转 camelCase：`--text-file` → flags.textFile。
//   6. 对 `api call` 的裸 JSON / `api call --data '{"k":"v"}'` 都正确透传。

const REPEATABLE = new Set(["--ignore"]);

function dashToCamel(s) {
  return s.replace(/-([a-z0-9])/gi, (_, ch) => ch.toUpperCase());
}

function isFlag(token) {
  return typeof token === "string" && token.startsWith("-");
}

export function parseArgs(argv) {
  const resource = argv[0] ?? null;
  let action = null;
  let start = 1;
  if (argv.length > 1 && !isFlag(argv[1])) {
    action = argv[1];
    start = 2;
  }
  const flags = {};
  for (let i = start; i < argv.length; i++) {
    const a = argv[i];
    if (a === "-h" || a === "--help") { flags.help = true; continue; }
    if (!a.startsWith("--")) continue;

    const key = dashToCamel(a.slice(2));
    const next = argv[i + 1];

    if (REPEATABLE.has(a)) {
      if (next !== undefined && !isFlag(next)) {
        (flags[key] ??= []).push(next);
        i++;
      } else {
        (flags[key] ??= []);
      }
      continue;
    }

    if (next === undefined || isFlag(next)) {
      flags[key] = true;
    } else {
      flags[key] = next;
      i++;
    }
  }
  return { resource, action, flags };
}
