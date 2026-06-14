@echo off
chcp 65001 >nul
setlocal

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

for /f "delims=" %%a in ('wsl wslpath "%PROJECT_DIR%"') do set "WSL_PROJECT_DIR=%%a"

echo ==========================================
echo   tts-work one-click startup
echo   Project: %PROJECT_DIR%
echo   WSL:     %WSL_PROJECT_DIR%
echo ==========================================
echo.

wsl --status >nul 2>&1
if errorlevel 1 (
    echo [ERROR] WSL2 is not available.
    echo Install: wsl --install -d Ubuntu-24.04
    pause
    exit /b 1
)

curl -s http://127.0.0.1:8765/api/health >nul 2>&1
if errorlevel 1 (
    echo [1/2] Starting backend in WSL2...
    start "tts-work backend" cmd /k "call \"%~dp0start-backend.bat\""
) else (
    echo [1/2] Backend already running, skipping.
)

echo [2/2] Starting frontend...
start "tts-work frontend" cmd /k "call \"%~dp0start-frontend.bat\""

echo.
echo Both processes launched in separate windows.
echo First startup downloads ~5GB model; please wait.
pause
