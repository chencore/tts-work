#!/bin/bash
set -e
echo "=== Step 1: Download miniconda installer (Tsinghua mirror) ==="
cd ~
if [ ! -f /tmp/miniconda.sh ]; then
  wget -q --show-progress -O /tmp/miniconda.sh \
    https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-x86_64.sh
fi
ls -lh /tmp/miniconda.sh

echo "=== Step 2: Install miniconda to ~/miniconda3 (no sudo) ==="
if [ ! -d ~/miniconda3 ]; then
  bash /tmp/miniconda.sh -b -p ~/miniconda3
fi
echo "Installed."

echo "=== Step 3: Initialize conda for bash ==="
~/miniconda3/bin/conda init bash 2>&1 | tail -5 || true

echo "=== Step 4: conda info ==="
~/miniconda3/bin/conda --version
~/miniconda3/bin/conda info --envs
