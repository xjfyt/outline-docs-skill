# Outline docs skill — Windows PowerShell launcher.
#
# 解析顺序：python(+httpx) → python3(+httpx) → uv（临时注入 httpx）→ node(>=18)
# 所有缓存重定向到 $env:LOCALAPPDATA\outline-skill，绝不污染 skill 目录。
#
# 可选环境变量：
#   OUTLINE_RUN_VIA     强制运行方式：uv | python | python3 | node
#   OUTLINE_PIP_MIRROR  pip 镜像（默认清华）
#   OUTLINE_CACHE_DIR   存放 uv / pycache 的根目录

$ErrorActionPreference = 'Stop'

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Definition
$SkillRoot  = Split-Path -Parent $ScriptDir
$PyCli      = Join-Path $SkillRoot 'python\outline_cli.py'
$NodeCli    = Join-Path $SkillRoot 'node\outline_cli.mjs'

if (-not $env:OUTLINE_PIP_MIRROR) {
    $env:OUTLINE_PIP_MIRROR = 'https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple'
}
if (-not $env:OUTLINE_CACHE_DIR) {
    $env:OUTLINE_CACHE_DIR = Join-Path $env:LOCALAPPDATA 'outline-skill'
}
if (-not (Test-Path $env:OUTLINE_CACHE_DIR)) {
    New-Item -ItemType Directory -Path $env:OUTLINE_CACHE_DIR -Force | Out-Null
}

$env:PYTHONPYCACHEPREFIX = Join-Path $env:OUTLINE_CACHE_DIR 'pycache'
if (-not $env:UV_CACHE_DIR) {
    $env:UV_CACHE_DIR = Join-Path $env:OUTLINE_CACHE_DIR 'uv'
}

function Test-PythonWithHttpx([string]$exe) {
    if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { return $false }
    & $exe -c "import httpx" *> $null
    return ($LASTEXITCODE -eq 0)
}

function Test-UvAvailable {
    return [bool](Get-Command uv -ErrorAction SilentlyContinue)
}

function Test-NodeAvailable {
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) { return $false }
    $major = & node -e "process.stdout.write(process.versions.node.split('.')[0])"
    return ([int]$major -ge 18)
}

function Invoke-Python([string]$exe, [string[]]$cliArgs) {
    & $exe $PyCli @cliArgs
    exit $LASTEXITCODE
}

function Invoke-Uv([string[]]$cliArgs) {
    & uv run --quiet --no-project --with httpx --cache-dir $env:UV_CACHE_DIR python $PyCli @cliArgs
    exit $LASTEXITCODE
}

function Invoke-Node([string[]]$cliArgs) {
    & node $NodeCli @cliArgs
    exit $LASTEXITCODE
}

function Write-FailHelp {
    Write-Host ""
    Write-Host "[ERROR] 未找到可用的运行时（需 python/python3 + httpx，或 uv，或 Node >= 18）。" -ForegroundColor Red
    Write-Host ""
    Write-Host "推荐方案（任选其一）："
    Write-Host ""
    Write-Host "  1) 安装 uv（最省事；httpx 按需注入到用户缓存，不碰 skill 目录）："
    Write-Host '     powershell -c "irm https://astral.sh/uv/install.ps1 | iex"'
    Write-Host ""
    Write-Host "  2) 已有 Python 时安装 httpx（清华镜像加速）："
    Write-Host "     python -m pip install --user httpx -i $env:OUTLINE_PIP_MIRROR"
    Write-Host ""
    Write-Host "  3) 前端开发者：安装 Node.js >= 18（https://nodejs.org 或 nvm-windows / fnm）"
    Write-Host ""
    Write-Host "诊断变量："
    Write-Host "  `$env:OUTLINE_RUN_VIA = 'uv' | 'python' | 'python3' | 'node'"
    Write-Host "  `$env:OUTLINE_PIP_MIRROR = 'https://your.mirror/simple'"
    Write-Host "  `$env:OUTLINE_CACHE_DIR = 'C:\custom\path'"
    exit 1
}

$runVia = if ($env:OUTLINE_RUN_VIA) { $env:OUTLINE_RUN_VIA.ToLower() } else { 'auto' }

switch ($runVia) {
    'python'  { if (Test-PythonWithHttpx 'python')  { Invoke-Python 'python'  $args } else { Write-FailHelp } }
    'python3' { if (Test-PythonWithHttpx 'python3') { Invoke-Python 'python3' $args } else { Write-FailHelp } }
    'uv'      { if (Test-UvAvailable)               { Invoke-Uv               $args } else { Write-FailHelp } }
    'node'    { if (Test-NodeAvailable)             { Invoke-Node             $args } else { Write-FailHelp } }
    'auto' {
        if (Test-PythonWithHttpx 'python')  { Invoke-Python 'python'  $args }
        if (Test-PythonWithHttpx 'python3') { Invoke-Python 'python3' $args }
        if (Test-UvAvailable)               { Invoke-Uv               $args }
        if (Test-NodeAvailable)             { Invoke-Node             $args }
        Write-FailHelp
    }
    default {
        Write-Host "[ERROR] 未知 OUTLINE_RUN_VIA 值：$runVia（可用：auto|python|python3|uv|node）" -ForegroundColor Red
        exit 2
    }
}
