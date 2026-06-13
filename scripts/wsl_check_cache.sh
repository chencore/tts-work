#!/bin/bash
echo "=== HF cache size ==="
du -sh ~/.cache/huggingface/ 2>/dev/null
echo "=== blobs ==="
ls -la ~/.cache/huggingface/hub/models--rednote-hilab--dots.tts-base/blobs/ 2>/dev/null | head -20
echo "=== snapshots ==="
ls ~/.cache/huggingface/hub/models--rednote-hilab--dots.tts-base/snapshots/*/ 2>/dev/null
