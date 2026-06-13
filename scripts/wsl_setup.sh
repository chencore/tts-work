#!/bin/bash
set -e
echo "=== whoami ==="
whoami
echo "=== sudo check ==="
sudo -n true 2>&1 && echo "passwordless sudo OK" || echo "sudo requires password"
echo "=== apt packages ==="
dpkg -l | grep -E "python3-venv|python3-pip|python3-dev|build-essential" | head -10
echo "=== python ==="
which python3
python3 --version
which pip3 2>&1
echo "=== mount check ==="
ls /mnt/d/code/tts-work/backend/ 2>&1 | head -5
