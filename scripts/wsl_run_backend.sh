#!/bin/bash
# Start backend in WSL2 with HF mirror for faster model download
source ~/miniconda3/etc/profile.d/conda.sh
conda activate dots_tts
cd /mnt/d/code/tts-work
export HF_ENDPOINT=https://hf-mirror.com
exec python -m backend.app
