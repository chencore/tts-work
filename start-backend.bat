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

echo Starting backend...
echo Project WSL path: %WSL_PROJECT_DIR%

wsl -d Ubuntu-24.04 -- bash "%WSL_PROJECT_DIR%/scripts/wsl_run_backend.sh"
