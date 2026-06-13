#!/bin/bash
set -e
source ~/miniconda3/etc/profile.d/conda.sh

echo "=== Step 0: Accept conda ToS ==="
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main 2>&1 || true
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r 2>&1 || true

echo "=== Step 1: Create conda env dots_tts (Python 3.10) ==="
if ! conda env list | grep -q "^dots_tts "; then
  conda create -n dots_tts python=3.10 -y
fi
conda activate dots_tts
python --version
which python pip

echo "=== Step 2: Configure pip to use Tsinghua mirror ==="
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
pip config set install.trusted-host pypi.tuna.tsinghua.edu.cn
pip install --upgrade pip

echo "=== Step 3: Install fastapi + uvicorn ==="
pip install --progress-bar off "fastapi>=0.110,<1.0" "uvicorn[standard]>=0.27,<1.0"

echo "=== Step 4: Install dots.tts from local clone ==="
# dots.tts is mounted from Windows; clone lives at /mnt/d/code/dots.tts
DOTS_TTS_PATH=/mnt/d/code/dots.tts
if [ ! -d "$DOTS_TTS_PATH" ]; then
  echo "ERROR: $DOTS_TTS_PATH does not exist"
  exit 1
fi

pip install --progress-bar off -e "$DOTS_TTS_PATH" \
  -c "$DOTS_TTS_PATH/constraints/recommended.txt"

echo "=== Step 5: Verify torch+CUDA ==="
python -c "import torch; print('torch', torch.__version__, 'cuda', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'no-gpu')"

echo "=== Step 6: Verify dots_tts imports ==="
python -c "from dots_tts.runtime import DotsTtsRuntime; print('dots_tts imports OK')"

echo "=== DONE ==="

