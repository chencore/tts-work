"""FastAPI app exposing /api/health.

Module import triggers `import backend.runtime`, which synchronously loads the
dots.tts model. The first request thus blocks until the model is ready.
"""

from __future__ import annotations

import logging
import os
import time

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import runtime

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


def main() -> None:
    port = int(os.environ.get("TTS_PORT", "8765"))
    logger.info("Starting backend on http://127.0.0.1:%d", port)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
