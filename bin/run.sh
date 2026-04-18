#!/usr/bin/env bash
# Outline docs skill — macOS / Linux launcher.
#
# 解析顺序：python3(+httpx) → python(+httpx) → uv（临时注入 httpx）→ node(>=18)
# 所有缓存都被重定向到用户目录 / 系统临时目录，绝不污染 skill 目录。
#
# 可选环境变量：
#   OUTLINE_RUN_VIA     强制运行方式：uv | python3 | python | node
#   OUTLINE_PIP_MIRROR  pip 镜像（默认清华）
#   OUTLINE_CACHE_DIR   存放 uv / pycache 的根目录（默认 $XDG_CACHE_HOME 或 ~/.cache）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PY_CLI="$SKILL_ROOT/python/outline_cli.py"
NODE_CLI="$SKILL_ROOT/node/outline_cli.mjs"

PIP_MIRROR="${OUTLINE_PIP_MIRROR:-https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple}"
CACHE_ROOT="${OUTLINE_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/outline-skill}"
mkdir -p "$CACHE_ROOT"

# 把 Python 的 __pycache__ 重定向到用户缓存目录，skill 内永不生成 .pyc
export PYTHONPYCACHEPREFIX="$CACHE_ROOT/pycache"
# 给 uv 一个专属缓存位置（仍在用户空间，不在 skill 内）
export UV_CACHE_DIR="${UV_CACHE_DIR:-$CACHE_ROOT/uv}"

run_via="${OUTLINE_RUN_VIA:-auto}"

try_python_with_httpx() {
  local py="$1"; shift
  if command -v "$py" >/dev/null 2>&1 && "$py" -c "import httpx" >/dev/null 2>&1; then
    exec "$py" "$PY_CLI" "$@"
  fi
  return 1
}

try_uv() {
  if command -v uv >/dev/null 2>&1; then
    # --no-project：忽略 cwd 下的 pyproject.toml；不在 skill 目录创建 .venv
    exec uv run --quiet --no-project --with httpx --cache-dir "$UV_CACHE_DIR" \
         python "$PY_CLI" "$@"
  fi
  return 1
}

try_node() {
  if command -v node >/dev/null 2>&1; then
    local ver
    ver="$(node -e 'process.stdout.write(process.versions.node.split(".")[0])')"
    if [ "$ver" -ge 18 ]; then
      exec node "$NODE_CLI" "$@"
    fi
  fi
  return 1
}

case "$run_via" in
  uv)      try_uv                           "$@" ;;
  python3) try_python_with_httpx python3    "$@" ;;
  python)  try_python_with_httpx python     "$@" ;;
  node)    try_node                         "$@" ;;
  auto)
    try_python_with_httpx python3 "$@" || true
    try_python_with_httpx python  "$@" || true
    try_uv                        "$@" || true
    try_node                      "$@" || true
    ;;
esac

cat >&2 <<EOF
❌ 未找到可用的运行时（需 python3/python + httpx，或 uv，或 Node >= 18）。

推荐方案（任选其一）：

  1) 安装 uv（最省事；httpx 按需注入到用户缓存，不碰 skill 目录）：
     curl -LsSf https://astral.sh/uv/install.sh | sh

  2) 已有 Python 时安装 httpx（清华镜像加速）：
     python3 -m pip install --user httpx -i $PIP_MIRROR
     # 或：python -m pip install --user httpx -i $PIP_MIRROR

  3) 前端开发者：安装 Node.js >= 18（https://nodejs.org 或 nvm / fnm）

诊断变量：
  OUTLINE_RUN_VIA=uv|python3|python|node
  OUTLINE_PIP_MIRROR=https://your.mirror/simple
  OUTLINE_CACHE_DIR=/custom/path        # 默认 \$XDG_CACHE_HOME/outline-skill
EOF
exit 1
