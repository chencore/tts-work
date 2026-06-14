@echo off
setlocal enabledelayedexpansion

REM tts-work 一键启动脚本（开发模式）
REM 同时启动 WSL2 后端和 Tauri 前端，分别开在两个独立窗口

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

REM 将 Windows 路径转换为 WSL 路径
for /f "delims=" %%a in ('wsl wslpath "%PROJECT_DIR%"') do set "WSL_PROJECT_DIR=%%a"

echo ==========================================
echo   tts-work 一键启动
echo   项目：%PROJECT_DIR%
echo   WSL： %WSL_PROJECT_DIR%
echo ==========================================
echo.

REM 检查 WSL2 是否可用
wsl --status >nul 2>&1
if errorlevel 1 (
    echo [错误] WSL2 不可用，请先安装并启用 WSL2 + Ubuntu-24.04。
    echo 安装命令：wsl --install -d Ubuntu-24.04
    pause
    exit /b 1
)

REM 检查后端是否已在运行
curl -s http://127.0.0.1:8765/api/health >nul 2>&1
if errorlevel 1 (
    echo [1/2] 启动后端（WSL2）...
    start "tts-work backend" cmd /k "wsl -d Ubuntu-24.04 -- bash \"%WSL_PROJECT_DIR%/scripts/wsl_run_backend.sh\""
) else (
    echo [1/2] 后端已在运行，跳过。
)

REM 检查 Node.js 可用性
where node >nul 2>&1
if errorlevel 1 (
    if exist "C:\Program Files (x86)\nvm\v24.15.0\node.exe" (
        echo [提示] 使用 nvm v24.15.0 的 Node.js
        set "NODE_DIR=C:\Program Files (x86)\nvm\v24.15.0"
    ) else if exist "C:\Program Files\nodejs\node.exe" (
        echo [提示] 使用系统安装的 Node.js
        set "NODE_DIR=C:\Program Files\nodejs"
    ) else (
        echo [错误] 找不到 Node.js，请安装 Node.js 18+ 或 nvm-windows。
        pause
        exit /b 1
    )
)

echo [2/2] 启动前端（Tauri）...
if defined NODE_DIR (
    start "tts-work frontend" cmd /k "cd /d \"%PROJECT_DIR%\" ^&^& set \"PATH=%NODE_DIR%;%PATH%\" ^&^& tauri dev"
) else (
    start "tts-work frontend" cmd /k "cd /d \"%PROJECT_DIR%\" ^&^& tauri dev"
)

echo.
echo 两个进程已分别在独立窗口启动：
echo   - 后端窗口：模型加载完成后，curl http://127.0.0.1:8765/api/health 返回 ready
echo   - 前端窗口：Tauri 桌面窗口弹出后会自动轮询后端状态
echo.
echo 提示：首次启动需下载 ~5GB 模型，请耐心等待。
pause
