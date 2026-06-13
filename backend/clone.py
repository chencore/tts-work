"""Single-segment continuation clone: synthesize + encode wav bytes.

This module wraps `dots.tts.runtime.generate()`, encodes the resulting
torch Tensor as 16-bit PCM wav bytes via soundfile, and normalizes errors
to fastapi.HTTPException with appropriate status codes.
"""

from __future__ import annotations

import io
from typing import Literal

import soundfile as sf
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
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"合成失败：{type(e).__name__}: {e}",
        )

    audio: "torch.Tensor" = result["audio"]  # type: ignore[name-defined]
    sample_rate: int = result["sample_rate"]
    if audio.ndim == 2:
        audio = audio.squeeze(0)
    audio_np = audio.cpu().float().numpy()

    buf = io.BytesIO()
    sf.write(buf, audio_np, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()
