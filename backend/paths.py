"""Windows → WSL2 path conversion + audio file validation.

The dots.tts runtime consumes a POSIX path under WSL2's filesystem view
(`/mnt/<drive>/...`). The Tauri frontend hands us a Windows path
(`D:\\...`); we convert here so call sites stay clean.
"""

from __future__ import annotations

import re
from pathlib import Path

WIN_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


def win_to_wsl2(path: str) -> str:
    """Convert a Windows local-disk path to its WSL2 view.

    D:\\audio\\ref.wav  ->  /mnt/d/audio/ref.wav
    C:/Users/ck/a.wav   ->  /mnt/c/Users/ck/a.wav

    Raises ValueError for UNC, network, or relative paths.
    """
    if not WIN_PATH_RE.match(path):
        raise ValueError(
            f"不支持的路径格式（仅本地盘 X:\\...）：{path}"
        )
    drive = path[0].lower()
    rest = path[2:].replace("\\", "/")
    return f"/mnt/{drive}{rest}"


def validate_prompt_audio(wsl2_path: str) -> None:
    """Validate the prompt audio path. Raises on invalid.

    - Must start with /mnt/
    - Must be an existing file
    - Must have a known audio extension
    """
    if not wsl2_path.startswith("/mnt/"):
        raise ValueError(f"参考音频路径必须在 /mnt/ 下：{wsl2_path}")
    p = Path(wsl2_path)
    if not p.is_file():
        raise FileNotFoundError(f"参考音频文件不存在：{wsl2_path}")
    if p.suffix.lower() not in AUDIO_EXTENSIONS:
        raise ValueError(
            f"不支持的音频格式：{p.suffix}（允许：{sorted(AUDIO_EXTENSIONS)}）"
        )
