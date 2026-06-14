@echo off
chcp 65001 >nul
setlocal

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

REM Try to find Node.js
set "NODE_DIR="
where node >nul 2>&1
if errorlevel 1 (
    if exist "C:\Program Files (x86)\nvm\v24.15.0\node.exe" (
        set "NODE_DIR=C:\Program Files (x86)\nvm\v24.15.0"
    ) else if exist "C:\Program Files\nodejs\node.exe" (
        set "NODE_DIR=C:\Program Files\nodejs"
    ) else (
        echo [ERROR] Node.js not found. Please install Node.js 18+ or nvm-windows.
        pause
        exit /b 1
    )
)

cd /d "%PROJECT_DIR%"
if defined NODE_DIR (
    echo Using Node.js from: %NODE_DIR%
    set "PATH=%NODE_DIR%;%PATH%"
)

tauri dev
