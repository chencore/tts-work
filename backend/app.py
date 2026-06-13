"""FastAPI app exposing /api/health.

Module import triggers `import backend.runtime`, which synchronously loads the
dots.tts model. The first request thus blocks until the model is ready.
"""

from __future__ import annotations

import logging
import os
import time

import uvicorn
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend import clone, runtime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="tts-work backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    state = runtime.get_state()
    return {
        "status": state.status,
        "model": state.model_name,
        "gpu": state.gpu_name,
        "elapsed_ms": int((time.time() - state.load_started_at) * 1000),
        "error": state.error,
    }


class CloneRequest(BaseModel):
    text: str = Field(..., min_length=1)
    prompt_audio_path: str = Field(..., min_length=1)
    prompt_text: str = Field(..., min_length=1)
    num_steps: int = Field(clone.DEFAULT_NUM_STEPS, ge=1, le=100)
    guidance_scale: float = Field(clone.DEFAULT_GUIDANCE, ge=0.0, le=10.0)
    language: str = Field("zh", pattern="^(zh|none)$")


@app.post("/api/clone")
def clone_route(req: CloneRequest) -> Response:
    wav_bytes = clone.synthesize_clone(
        text=req.text,
        prompt_audio_path=req.prompt_audio_path,
        prompt_text=req.prompt_text,
        num_steps=req.num_steps,
        guidance_scale=req.guidance_scale,
        language=req.language,
    )
    return Response(content=wav_bytes, media_type="audio/wav")


def main() -> None:
    port = int(os.environ.get("TTS_PORT", "8765"))
    logger.info("Starting backend on http://127.0.0.1:%d", port)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
