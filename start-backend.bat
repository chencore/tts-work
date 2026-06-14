@echo off
chcp 65001 >nul
setlocal

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

for /f "delims=" %%a in ('wsl wslpath "%PROJECT_DIR%"') do set "WSL_PROJECT_DIR=%%a"

echo Starting backend...
echo Project WSL path: %WSL_PROJECT_DIR%

wsl -d Ubuntu-24.04 -- bash "%WSL_PROJECT_DIR%/scripts/wsl_run_backend.sh"
