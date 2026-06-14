"""dots.tts runtime singleton.

Module import triggers synchronous model load. Subsequent imports reuse the
loaded runtime — no reload per request.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Literal

import torch

logger = logging.getLogger(__name__)

Status = Literal["loading", "ready", "error"]


@dataclass
class RuntimeState:
    status: Status
    model_name: str
    gpu_name: str | None
    load_started_at: float
    error: str | None


_STATE: RuntimeState = RuntimeState(
    status="loading",
    model_name=os.environ.get("DOTS_TTS_MODEL", "rednote-hilab/dots.tts-base"),
    gpu_name=None,
    load_started_at=time.time(),
    error=None,
)

_RUNTIME: Any = None


def _load() -> None:
    """Synchronously load dots.tts model. Called at module import."""
    global _RUNTIME, _STATE
    try:
        if torch.cuda.is_available():
            _STATE.gpu_name = torch.cuda.get_device_name(0)
            logger.info("GPU detected: %s", _STATE.gpu_name)
        else:
            _STATE.gpu_name = None
            logger.warning("No CUDA GPU detected; dots.tts will fail to load")

        from dots_tts.runtime import DotsTtsRuntime

        logger.info("Loading dots.tts model: %s", _STATE.model_name)
        max_length = int(os.environ.get("DOTS_TTS_MAX_LENGTH", "400"))
        _RUNTIME = DotsTtsRuntime.from_pretrained(
            _STATE.model_name,
            precision="bfloat16",
            max_generate_length=max_length,
        )
        _STATE = RuntimeState(
            status="ready",
            model_name=_STATE.model_name,
            gpu_name=_STATE.gpu_name,
            load_started_at=_STATE.load_started_at,
            error=None,
        )
        elapsed = time.time() - _STATE.load_started_at
        logger.info("dots.tts model ready (loaded in %.1fs)", elapsed)

    except Exception as exc:
        _STATE = RuntimeState(
            status="error",
            model_name=_STATE.model_name,
            gpu_name=_STATE.gpu_name,
            load_started_at=_STATE.load_started_at,
            error=f"{type(exc).__name__}: {exc}",
        )
        logger.exception("dots.tts model failed to load")


def get_state() -> RuntimeState:
    return _STATE


def get_runtime() -> Any:
    if _STATE.status != "ready" or _RUNTIME is None:
        raise RuntimeError(f"runtime not ready (status={_STATE.status})")
    return _RUNTIME


_load()
