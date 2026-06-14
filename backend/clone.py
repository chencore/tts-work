"""Single-segment continuation clone: synthesize + encode wav bytes.

This module wraps `dots.tts.runtime.generate()`, encodes the resulting
torch Tensor as 16-bit PCM wav bytes via soundfile, and normalizes errors
to fastapi.HTTPException with appropriate status codes.
"""

from __future__ import annotations

import io
from typing import Literal

import soundfile as sf
import torch
from fastapi import HTTPException

from .paths import validate_prompt_audio
from .runtime import get_runtime

DEFAULT_NUM_STEPS = 10
DEFAULT_GUIDANCE = 1.2
DEFAULT_LANGUAGE: Literal["zh", "none"] = "zh"


def synthesize_clone(
    *,
    text: str,
    prompt_audio_path: str,
    prompt_text: str,
    num_steps: int = DEFAULT_NUM_STEPS,
    guidance_scale: float = DEFAULT_GUIDANCE,
    language: str = DEFAULT_LANGUAGE,
) -> bytes:
    """Synthesize a single segment via dots.tts continuation mode.

    Args:
        text: Target text to synthesize.
        prompt_audio_path: WSL2 path to reference audio file.
        prompt_text: Transcript of reference audio.
        num_steps: ODE solver steps (default 10).
        guidance_scale: Guidance strength (default 1.2, dots.tts default).
        language: "zh" or "none".

    Returns:
        wav bytes (48kHz mono, 16-bit PCM).

    Raises:
        HTTPException: 400 (bad path/file), 422 (empty text),
            413 (text too long), 500 (synthesis failure).
    """
    try:
        validate_prompt_audio(prompt_audio_path)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=f"参考音频无效：{e}")

    if not text.strip():
        raise HTTPException(status_code=422, detail="目标文本不能为空")
    if not prompt_text.strip():
        raise HTTPException(status_code=422, detail="参考转录不能为空")

    try:
        runtime = get_runtime()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        result = runtime.generate(
            text=text,
            prompt_audio_path=prompt_audio_path,
            prompt_text=prompt_text,
            language=None if language == "none" else language,
            num_steps=num_steps,
            guidance_scale=guidance_scale,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=413,
            detail=f"文本过长或不被模型接受：{e}",
        )
    except RuntimeError as e:
        msg = str(e)
        if "out of memory" in msg.lower() or "CUDA error: out of memory" in msg:
            raise HTTPException(
                status_code=503,
                detail=(
                    "显存不足：当前输入对 GPU 显存压力过大。"
                    "请尝试：1）缩短目标文本；2）缩短参考音频；"
                    "3）降低高级参数中的 num_steps；"
                    "4）在 WSL2 中设置 DOTS_TTS_MAX_LENGTH=300 后重启后端。"
                ),
            )
        raise HTTPException(status_code=500, detail=f"合成失败：{type(e).__name__}: {e}")
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        if "NoBackendError" in msg or "No backend" in msg:
            msg = (
                "参考音频解码失败：WSL2 缺少 ffmpeg，"
                "无法读取 mp3/m4a 等格式。请在 WSL2 中运行："
                "sudo apt-get update && sudo apt-get install -y ffmpeg"
            )
        raise HTTPException(
            status_code=500,
            detail=f"合成失败：{msg}",
        )

    audio: "torch.Tensor" = result["audio"]  # type: ignore[name-defined]
    sample_rate: int = result["sample_rate"]
    while audio.ndim > 1 and audio.shape[0] == 1:
        audio = audio.squeeze(0)
    if audio.ndim != 1:
        raise HTTPException(
            status_code=500,
            detail=f"合成失败：音频维度异常 {tuple(audio.shape)}，无法编码为 WAV",
        )
    audio_np = audio.cpu().float().numpy()

    buf = io.BytesIO()
    sf.write(buf, audio_np, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()
