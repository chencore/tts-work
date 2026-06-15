@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

REM Convert Windows path (D:\code\tts-work) to WSL path (/mnt/d/code/tts-work).
REM wsl wslpath can return /mnt/host/... on some cross-distro setups, which may
REM not be accessible, so we build the classic /mnt/<drive> path manually.
set "WSL_PROJECT_DIR=%PROJECT_DIR%"
set "WSL_PROJECT_DIR=!WSL_PROJECT_DIR:\=/!"
set "DRIVE=!WSL_PROJECT_DIR:~0,1!"
for %%a in ("A=a" "B=b" "C=c" "D=d" "E=e" "F=f" "G=g" "H=h" "I=i" "J=j" "K=k" "L=l" "M=m" "N=n" "O=o" "P=p" "Q=q" "R=r" "S=s" "T=t" "U=u" "V=v" "W=w" "X=x" "Y=y" "Z=z") do (
    for /f "tokens=1,2 delims==" %%b in (%%a) do (
        if "!DRIVE!"=="%%b" set "DRIVE=%%c"
    )
)
set "WSL_PROJECT_DIR=/mnt/%DRIVE%%WSL_PROJECT_DIR:~2%"

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
    start "tts-work backend" "%~dp0start-backend.bat"
) else (
    echo [1/2] Backend already running, skipping.
)

echo [2/2] Starting frontend...
start "tts-work frontend" "%~dp0start-frontend.bat"

echo.
echo Both processes launched in separate windows.
echo First startup downloads ~5GB model; please wait.
pause
