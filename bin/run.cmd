@echo off
rem Outline docs skill -- Windows launcher.
rem
rem 解析顺序：python(+httpx) -> python3(+httpx) -> uv -> node(>=18)
rem 所有缓存重定向到 %LOCALAPPDATA%\outline-skill，绝不污染 skill 目录。
rem
rem 可选环境变量：
rem   OUTLINE_RUN_VIA     强制运行方式：uv | python | python3 | node
rem   OUTLINE_PIP_MIRROR  pip 镜像（默认清华）
rem   OUTLINE_CACHE_DIR   存放 uv / pycache 的根目录
rem                       （默认 %LOCALAPPDATA%\outline-skill）

setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "SKILL_ROOT=%%~fI"
set "PY_CLI=%SKILL_ROOT%\python\outline_cli.py"
set "NODE_CLI=%SKILL_ROOT%\node\outline_cli.mjs"

if "%OUTLINE_PIP_MIRROR%"=="" set "OUTLINE_PIP_MIRROR=https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
if "%OUTLINE_CACHE_DIR%"=="" set "OUTLINE_CACHE_DIR=%LOCALAPPDATA%\outline-skill"
if not exist "%OUTLINE_CACHE_DIR%" mkdir "%OUTLINE_CACHE_DIR%" 2>nul

set "PYTHONPYCACHEPREFIX=%OUTLINE_CACHE_DIR%\pycache"
if "%UV_CACHE_DIR%"=="" set "UV_CACHE_DIR=%OUTLINE_CACHE_DIR%\uv"

set "RUN_VIA=%OUTLINE_RUN_VIA%"
if "%RUN_VIA%"=="" set "RUN_VIA=auto"

if /I "%RUN_VIA%"=="uv"      goto :try_uv
if /I "%RUN_VIA%"=="python"  goto :try_python
if /I "%RUN_VIA%"=="python3" goto :try_python3
if /I "%RUN_VIA%"=="node"    goto :try_node

rem --- auto mode ---------------------------------------------------------
call :detect_python python && goto :run_python
call :detect_python python3 && goto :run_python
call :detect_uv && goto :run_uv
call :detect_node && goto :run_node
goto :fail

:try_python
call :detect_python python && goto :run_python
goto :fail

:try_python3
call :detect_python python3 && goto :run_python
goto :fail

:try_uv
call :detect_uv && goto :run_uv
goto :fail

:try_node
call :detect_node && goto :run_node
goto :fail

rem --- detectors ---------------------------------------------------------
:detect_python
where %1 >nul 2>&1 || exit /b 1
%1 -c "import httpx" >nul 2>&1 || exit /b 1
set "PY_CMD=%1"
exit /b 0

:detect_uv
where uv >nul 2>&1 || exit /b 1
exit /b 0

:detect_node
where node >nul 2>&1 || exit /b 1
for /f %%V in ('node -e "process.stdout.write(process.versions.node.split(\".\")[0])"') do set "NODE_MAJOR=%%V"
if %NODE_MAJOR% LSS 18 exit /b 1
exit /b 0

rem --- runners -----------------------------------------------------------
:run_python
"%PY_CMD%" "%PY_CLI%" %*
exit /b %ERRORLEVEL%

:run_uv
uv run --quiet --no-project --with httpx --cache-dir "%UV_CACHE_DIR%" python "%PY_CLI%" %*
exit /b %ERRORLEVEL%

:run_node
node "%NODE_CLI%" %*
exit /b %ERRORLEVEL%

:fail
echo.
echo [ERROR] 未找到可用的运行时（需 python/python3 + httpx，或 uv，或 Node ^>= 18）。
echo.
echo 推荐方案（任选其一）：
echo.
echo   1) 安装 uv（最省事；httpx 按需注入到用户缓存，不碰 skill 目录）：
echo      powershell -c "irm https://astral.sh/uv/install.ps1 ^| iex"
echo.
echo   2) 已有 Python 时安装 httpx（清华镜像加速）：
echo      python -m pip install --user httpx -i %OUTLINE_PIP_MIRROR%
echo.
echo   3) 前端开发者：安装 Node.js ^>= 18（https://nodejs.org 或 nvm-windows / fnm）
echo.
echo 诊断变量：
echo   OUTLINE_RUN_VIA=uv^|python^|python3^|node
echo   OUTLINE_PIP_MIRROR=https://your.mirror/simple
echo   OUTLINE_CACHE_DIR=C:\custom\path
exit /b 1
