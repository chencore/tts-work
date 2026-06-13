# single-continuation-clone Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** v0.1 R-v0.1-ck-1 — 单段 continuation 克隆：用户在桌面 App 选参考音频 + 输入转录 + 目标文本 → 调 dots.tts 合成 → 试听 + 保存 wav。

**Architecture:** 前端 Tauri（Windows）拿文件路径转 WSL2 格式后 POST `/api/clone`，后端（WSL2 Python）调 `dots.tts.runtime.generate()` 合成，soundfile 编码 wav bytes 同步返回。前端用 Blob + `<audio>` 试听，Tauri `dialog.save()` + `fs.writeBinaryFile()` 直接写盘保存（不经后端）。

**Tech Stack:** FastAPI + soundfile + dots.tts（后端，WSL2）| React + Vite + TS + Tauri 2.x plugin-dialog/plugin-fs（前端，Windows）

---

## File Structure

**Create:**
- `backend/paths.py` — Windows→WSL2 路径转换 + `validate_prompt_audio`
- `backend/clone.py` — `synthesize_clone()` 合成 + soundfile wav 编码
- `frontend/src/paths.ts` — 前端 `winToWsl2()` 转换
- `frontend/src/components/AdvancedParams.tsx` — 折叠参数面板
- `frontend/src/pages/ClonePage.tsx` — 单段克隆主页面
- `backend/tests/__init__.py` — 测试包标识
- `backend/tests/test_paths.py` — paths.py 单元测试

**Modify:**
- `backend/app.py:35` — 注册 `POST /api/clone` 路由（在 `/api/health` 之后）
- `backend/requirements.txt` — 显式钉 `soundfile` 和 `pytest`
- `frontend/src/api.ts:44` — 末尾追加 `CloneParams` + `cloneSynth()`
- `frontend/src/App.tsx:63` — `view.kind === "ready"` 时渲染 `<ClonePage />`
- `frontend/package.json:12` — 加 `@tauri-apps/plugin-dialog` + `@tauri-apps/plugin-fs`
- `src-tauri/Cargo.toml:25` — 加 `tauri-plugin-dialog` + `tauri-plugin-fs` Rust 依赖
- `src-tauri/src/lib.rs:3` — 在 builder 链上注册两个 plugin
- `src-tauri/capabilities/default.json:8` — 授 dialog + fs 权限
- `spec/requirements.md:44` — 修订非目标里的参数描述

---

### Task 1: backend paths.py + unit tests

**Files:**
- Create: `backend/paths.py`
- Create: `backend/tests/__init__.py` (空文件)
- Create: `backend/tests/test_paths.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/__init__.py` as empty file (just `touch`).

Create `backend/tests/test_paths.py`:

```python
"""Unit tests for backend.paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.paths import win_to_wsl2, validate_prompt_audio


def test_win_to_wsl2_simple():
    assert win_to_wsl2("D:\\audio\\ref.wav") == "/mnt/d/audio/ref.wav"


def test_win_to_wsl2_forward_slash():
    assert win_to_wsl2("C:/Users/ck/a.wav") == "/mnt/c/Users/ck/a.wav"


def test_win_to_wsl2_lowercase_drive():
    assert win_to_wsl2("d:\\foo.wav") == "/mnt/d/foo.wav"


def test_win_to_wsl2_rejects_unc():
    with pytest.raises(ValueError, match="不支持的路径格式"):
        win_to_wsl2("\\\\server\\share\\ref.wav")


def test_win_to_wsl2_rejects_relative():
    with pytest.raises(ValueError, match="不支持的路径格式"):
        win_to_wsl2("audio/ref.wav")


def test_validate_prompt_audio_missing_file(tmp_path):
    fake = "/mnt/d/definitely_does_not_exist_xxx.wav"
    with pytest.raises(FileNotFoundError):
        validate_prompt_audio(fake)


def test_validate_prompt_audio_wrong_extension(tmp_path, monkeypatch):
    # 创建临时文件，绕过 /mnt/ 限制（直接 monkeypatch 校验）
    fake_wsl2 = tmp_path / "ref.txt"
    fake_wsl2.write_text("not audio")

    def fake_path(p):
        return tmp_path / Path(p).name

    monkeypatch.setattr("backend.paths.Path", lambda p: tmp_path / Path(p).name)
    # 上面 monkeypatch 之后 .suffix 还能正常工作
    with pytest.raises(ValueError, match="不支持的音频格式"):
        validate_prompt_audio(str(fake_wsl2))
```

- [ ] **Step 2: Run test to verify it fails (module not found)**

Run (在 WSL2 里):
```bash
wsl -d Ubuntu-24.04 -- bash -c "source ~/miniconda3/etc/profile.d/conda.sh && conda activate dots_tts && cd /mnt/d/code/tts-work && python -m pytest backend/tests/test_paths.py -v 2>&1 | tail -10"
```

Expected: `ModuleNotFoundError: No module named 'backend.paths'` 或类似 import 失败。

- [ ] **Step 3: Install pytest in dots_tts env**

```bash
wsl -d Ubuntu-24.04 -- bash -c "source ~/miniconda3/etc/profile.d/conda.sh && conda activate dots_tts && pip install pytest -i https://pypi.tuna.tsinghua.edu.cn/simple 2>&1 | tail -5"
```

Expected: `Successfully installed pytest-8.x.x`

- [ ] **Step 4: Implement backend/paths.py**

Create `backend/paths.py`:

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

```bash
wsl -d Ubuntu-24.04 -- bash -c "source ~/miniconda3/etc/profile.d/conda.sh && conda activate dots_tts && cd /mnt/d/code/tts-work && python -m pytest backend/tests/test_paths.py -v 2>&1 | tail -15"
```

Expected: `7 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/paths.py backend/tests/
git commit -m "feat(backend): add Windows→WSL2 path conversion + validation

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: backend clone.py — synthesis + wav encoding

**Files:**
- Create: `backend/clone.py`

- [ ] **Step 1: Implement backend/clone.py**

Create `backend/clone.py`:

```python
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

    runtime = get_runtime()
    try:
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
```

- [ ] **Step 2: Smoke-check the import (without actually synthesizing)**

```bash
wsl -d Ubuntu-24.04 -- bash -c "source ~/miniconda3/etc/profile.d/conda.sh && conda activate dots_tts && cd /mnt/d/code/tts-work && python -c 'from backend.clone import synthesize_clone, DEFAULT_NUM_STEPS, DEFAULT_GUIDANCE, DEFAULT_LANGUAGE; print(DEFAULT_NUM_STEPS, DEFAULT_GUIDANCE, DEFAULT_LANGUAGE)' 2>&1 | tail -5"
```

Expected: `10 1.2 zh` (这条会触发 dots.tts 模型加载，需等待几十秒)。

- [ ] **Step 3: Commit**

```bash
git add backend/clone.py
git commit -m "feat(backend): add clone synthesis + wav encoding

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: backend app.py — register POST /api/clone route

**Files:**
- Modify: `backend/app.py` (add imports + CloneRequest schema + route after /api/health)

- [ ] **Step 1: Add imports and schema**

Edit `backend/app.py`. At the imports block (after `from fastapi.middleware.cors import CORSMiddleware` on line 15), add:

```python
from fastapi import Response
from pydantic import BaseModel, Field

from backend import clone
```

Actually replace the existing import block to include all needed names. Replace lines 13-17:

```python
import uvicorn
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend import clone, runtime
```

- [ ] **Step 2: Add CloneRequest schema and route after the health route**

Insert after line 44 (end of `health()` function), before `def main()`:

```python
class CloneRequest(BaseModel):
    text: str = Field(..., min_length=1)
    prompt_audio_path: str = Field(..., min_length=1)
    prompt_text: str = Field(..., min_length=1)
    num_steps: int = Field(DEFAULT_NUM_STEPS_VALUE, ge=1, le=100)
    guidance_scale: float = Field(DEFAULT_GUIDANCE_VALUE, ge=0.0, le=10.0)
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
```

Replace `DEFAULT_NUM_STEPS_VALUE` and `DEFAULT_GUIDANCE_VALUE` with the actual default references: `clone.DEFAULT_NUM_STEPS` and `clone.DEFAULT_GUIDANCE`. Final form:

```python
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
```

- [ ] **Step 3: Verify syntax (don't start server yet)**

```bash
wsl -d Ubuntu-24.04 -- bash -c "source ~/miniconda3/etc/profile.d/conda.sh && conda activate dots_tts && cd /mnt/d/code/tts-work && python -c 'from backend.app import app; print([r.path for r in app.routes])' 2>&1 | tail -3"
```

Expected: list including `/api/health` and `/api/clone`.

- [ ] **Step 4: Commit**

```bash
git add backend/app.py
git commit -m "feat(backend): register POST /api/clone route

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: backend requirements.txt — pin soundfile + pytest

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add explicit pins**

Edit `backend/requirements.txt`, append after the dots.tts block:

```
# Audio encoding (transitive via librosa, but pinned explicitly for stability)
soundfile>=0.12,<1.0

# Dev: pytest for backend unit tests
pytest>=8.0,<9.0
```

- [ ] **Step 2: Verify versions already installed match**

```bash
wsl -d Ubuntu-24.04 -- bash -c "source ~/miniconda3/etc/profile.d/conda.sh && conda activate dots_tts && python -c 'import soundfile, pytest; print(soundfile.__version__, pytest.__version__)'"
```

Expected: `0.13.1 8.x.x` (or compatible).

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "build(backend): pin soundfile + pytest explicitly

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: Tauri — add dialog + fs Rust plugins

**Files:**
- Modify: `src-tauri/Cargo.toml` (add deps)
- Modify: `src-tauri/src/lib.rs` (register plugins)

- [ ] **Step 1: Add Rust dependencies**

Edit `src-tauri/Cargo.toml` `[dependencies]` section. After `tauri-plugin-log = "2"` (line 25), add:

```toml
tauri-plugin-dialog = "2"
tauri-plugin-fs = "2"
```

- [ ] **Step 2: Register plugins in lib.rs**

Edit `src-tauri/src/lib.rs`. Replace the existing `run()` function body with:

```rust
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_dialog::init())
    .plugin(tauri_plugin_fs::init())
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
```

- [ ] **Step 3: Verify it compiles (will download crates, ~1-2 min)**

```bash
cd D:/code/tts-work/src-tauri && cargo check 2>&1 | tail -10
```

Expected: `Finished` (no errors). May show warnings, ignore.

- [ ] **Step 4: Commit**

```bash
git add src-tauri/Cargo.toml src-tauri/Cargo.lock src-tauri/src/lib.rs
git commit -m "feat(tauri): register dialog + fs plugins

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: Tauri — grant dialog + fs capabilities

**Files:**
- Modify: `src-tauri/capabilities/default.json`

- [ ] **Step 1: Add permissions**

Edit `src-tauri/capabilities/default.json`. Replace the file with:

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "enables the default permissions + dialog/fs for clone feature",
  "windows": [
    "main"
  ],
  "permissions": [
    "core:default",
    "dialog:allow-open",
    "dialog:allow-save",
    "fs:allow-write-binary-file",
    {
      "identifier": "fs:scope",
      "allow": [{ "path": "**" }]
    }
  ]
}
```

Note: `fs:scope` with `"**"` allows writing anywhere on disk. v0.1 dev convenience; `package-release` task will tighten.

- [ ] **Step 2: Verify capability schema valid**

```bash
cd D:/code/tts-work/src-tauri && cargo check 2>&1 | tail -10
```

Expected: still `Finished` (capabilities are checked at build time).

- [ ] **Step 3: Commit**

```bash
git add src-tauri/capabilities/default.json
git commit -m "feat(tauri): grant dialog + fs write permissions

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 7: frontend — install Tauri plugin npm packages

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install packages**

```bash
export PATH="/c/Program Files (x86)/nvm/v24.15.0:$PATH"
cd D:/code/tts-work/frontend && npm install @tauri-apps/plugin-dialog @tauri-apps/plugin-fs 2>&1 | tail -5
```

Expected: `added N packages` with no errors.

- [ ] **Step 2: Verify versions in package.json**

```bash
grep -E "plugin-(dialog|fs)" D:/code/tts-work/frontend/package.json
```

Expected: two lines with `@tauri-apps/plugin-dialog` and `@tauri-apps/plugin-fs`.

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "build(frontend): add Tauri dialog + fs plugin npm packages

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 8: frontend paths.ts — Windows→WSL2 conversion

**Files:**
- Create: `frontend/src/paths.ts`

- [ ] **Step 1: Implement paths.ts**

Create `frontend/src/paths.ts`:

```typescript
/** Windows path → WSL2 path conversion. Mirrors backend/paths.py:win_to_wsl2. */

const WIN_PATH_RE = /^[A-Za-z]:[\\/]/;

export function winToWsl2(path: string): string {
  if (!WIN_PATH_RE.test(path)) {
    throw new Error(`不支持的路径格式（仅本地盘 X:\\...）：${path}`);
  }
  const drive = path[0].toLowerCase();
  const rest = path.slice(2).replace(/\\/g, "/");
  return `/mnt/${drive}${rest}`;
}
```

- [ ] **Step 2: Smoke-verify via tsx**

```bash
cd D:/code/tts-work/frontend && npx tsx -e "import {winToWsl2} from './src/paths'; console.log(winToWsl2('D:\\\\audio\\\\ref.wav')); console.log(winToWsl2('C:/Users/ck/a.wav'));" 2>&1 | tail -3
```

Expected:
```
/mnt/d/audio/ref.wav
/mnt/c/Users/ck/a.wav
```

(If `tsx` not available, install with `npm install --save-dev tsx` first, or skip this check and rely on type-check.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/paths.ts
git commit -m "feat(frontend): add winToWsl2 path conversion

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 9: frontend api.ts — add cloneSynth

**Files:**
- Modify: `frontend/src/api.ts` (append after line 44)

- [ ] **Step 1: Add CloneParams and cloneSynth**

Edit `frontend/src/api.ts`. At the end of file (after line 44), append:

```typescript
export type CloneLanguage = "zh" | "none";

export interface CloneParams {
  text: string;
  promptAudioPath: string; // already WSL2-formatted
  promptText: string;
  numSteps?: number;
  guidanceScale?: number;
  language?: CloneLanguage;
}

export async function cloneSynth(params: CloneParams): Promise<Blob> {
  const body = {
    text: params.text,
    prompt_audio_path: params.promptAudioPath,
    prompt_text: params.promptText,
    num_steps: params.numSteps ?? 10,
    guidance_scale: params.guidanceScale ?? 1.2,
    language: params.language ?? "zh",
  };
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}/api/clone`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    throw new ApiError(
      e instanceof Error ? e.message : "network error",
      "network",
    );
  }
  if (!resp.ok) {
    let msg = `HTTP ${resp.status}`;
    try {
      const err = await resp.json();
      msg = typeof err.detail === "string" ? err.detail : msg;
    } catch {
      // body wasn't JSON, keep generic msg
    }
    throw new ApiError(msg, "http");
  }
  return await resp.blob();
}
```

- [ ] **Step 2: Verify type-check passes**

```bash
cd D:/code/tts-work/frontend && npx tsc --noEmit 2>&1 | tail -10
```

Expected: no errors. (If `erasableSyntaxOnly`/`verbatimModuleSyntax` issues arise, ensure `CloneLanguage` is imported as type where used.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api.ts
git commit -m "feat(frontend): add cloneSynth HTTP client

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 10: frontend AdvancedParams.tsx — collapsible panel

**Files:**
- Create: `frontend/src/components/AdvancedParams.tsx`

- [ ] **Step 1: Implement the component**

Create `frontend/src/components/AdvancedParams.tsx`:

```tsx
import type { CloneLanguage } from "../api";

export interface AdvancedParamValues {
  numSteps: number;
  guidanceScale: number;
  language: CloneLanguage;
}

interface Props {
  value: AdvancedParamValues;
  onChange: (next: AdvancedParamValues) => void;
}

export default function AdvancedParams({ value, onChange }: Props) {
  return (
    <details className="advanced-params">
      <summary>高级参数</summary>
      <div className="advanced-params-row">
        <label>
          num_steps:
          <input
            type="number"
            min={1}
            max={100}
            value={value.numSteps}
            onChange={(e) =>
              onChange({ ...value, numSteps: Number(e.target.value) })
            }
          />
        </label>
        <label>
          guidance_scale:
          <input
            type="number"
            step={0.1}
            min={0}
            max={10}
            value={value.guidanceScale}
            onChange={(e) =>
              onChange({ ...value, guidanceScale: Number(e.target.value) })
            }
          />
        </label>
        <label>
          language:
          <select
            value={value.language}
            onChange={(e) =>
              onChange({ ...value, language: e.target.value as CloneLanguage })
            }
          >
            <option value="zh">zh</option>
            <option value="none">none</option>
          </select>
        </label>
      </div>
    </details>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd D:/code/tts-work/frontend && npx tsc --noEmit 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/AdvancedParams.tsx
git commit -m "feat(frontend): add AdvancedParams collapsible panel

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 11: frontend ClonePage.tsx — main UI

**Files:**
- Create: `frontend/src/pages/ClonePage.tsx`

- [ ] **Step 1: Implement ClonePage**

Create `frontend/src/pages/ClonePage.tsx`:

```tsx
import { useState } from "react";
import { open, save } from "@tauri-apps/plugin-dialog";
import { writeBinaryFile } from "@tauri-apps/plugin-fs";

import { ApiError, cloneSynth } from "../api";
import AdvancedParams, {
  type AdvancedParamValues,
} from "../components/AdvancedParams";
import { winToWsl2 } from "../paths";

type SynthStatus =
  | { kind: "idle" }
  | { kind: "synthing" }
  | { kind: "done"; blobUrl: string }
  | { kind: "error"; message: string };

const DEFAULT_ADVANCED: AdvancedParamValues = {
  numSteps: 10,
  guidanceScale: 1.2,
  language: "zh",
};

export default function ClonePage() {
  const [text, setText] = useState("");
  const [promptWinPath, setPromptWinPath] = useState<string | null>(null);
  const [promptText, setPromptText] = useState("");
  const [advanced, setAdvanced] = useState<AdvancedParamValues>(DEFAULT_ADVANCED);
  const [status, setStatus] = useState<SynthStatus>({ kind: "idle" });
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  const canSynth =
    text.trim() && promptWinPath && promptText.trim() && status.kind !== "synthing";

  async function handlePickAudio() {
    try {
      const picked = await open({
        filters: [{ name: "音频", extensions: ["wav", "mp3", "flac", "ogg", "m4a"] }],
      });
      if (typeof picked === "string") {
        setPromptWinPath(picked);
      }
    } catch (e) {
      setStatus({
        kind: "error",
        message: `选择文件失败：${e instanceof Error ? e.message : String(e)}`,
      });
    }
  }

  async function handleSynth() {
    if (!promptWinPath) return;
    setSavedMsg(null);
    setStatus({ kind: "synthing" });
    let wsl2Path: string;
    try {
      wsl2Path = winToWsl2(promptWinPath);
    } catch (e) {
      setStatus({
        kind: "error",
        message: e instanceof Error ? e.message : String(e),
      });
      return;
    }
    try {
      const blob = await cloneSynth({
        text,
        promptAudioPath: wsl2Path,
        promptText,
        numSteps: advanced.numSteps,
        guidanceScale: advanced.guidanceScale,
        language: advanced.language,
      });
      // revoke previous blob url if any
      if (status.kind === "done") {
        URL.revokeObjectURL(status.blobUrl);
      }
      const blobUrl = URL.createObjectURL(blob);
      setStatus({ kind: "done", blobUrl });
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? `${e.kind === "network" ? "网络错误" : "后端错误"}：${e.message}`
          : e instanceof Error
            ? e.message
            : String(e);
      setStatus({ kind: "error", message: msg });
    }
  }

  async function handleSave() {
    if (status.kind !== "done") return;
    try {
      const target = await save({ defaultPath: "clone.wav" });
      if (!target) return;
      const buf = await (await fetch(status.blobUrl)).arrayBuffer();
      await writeBinaryFile(target, new Uint8Array(buf));
      setSavedMsg(`已保存到 ${target}`);
    } catch (e) {
      setSavedMsg(
        `保存失败：${e instanceof Error ? e.message : String(e)}`,
      );
    }
  }

  const fileName = promptWinPath
    ? promptWinPath.split(/[\\/]/).pop()
    : null;

  return (
    <section className="clone-page">
      <h2>单段克隆</h2>

      <label className="field">
        <span className="field-label">目标文本</span>
        <textarea
          rows={4}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="请输入要合成的中文文本..."
        />
      </label>

      <div className="field-row">
        <label className="field">
          <span className="field-label">参考音频</span>
          <button type="button" onClick={handlePickAudio}>
            选择文件
          </button>
          {fileName && <span className="hint">{fileName} ✓</span>}
        </label>
      </div>

      <label className="field">
        <span className="field-label">参考转录</span>
        <textarea
          rows={3}
          value={promptText}
          onChange={(e) => setPromptText(e.target.value)}
          placeholder="输入参考音频对应的文本..."
        />
      </label>

      <AdvancedParams value={advanced} onChange={setAdvanced} />

      <div className="actions">
        <button
          type="button"
          onClick={handleSynth}
          disabled={!canSynth}
        >
          {status.kind === "synthing" ? "合成中（可能需 10~30 秒）..." : "合成"}
        </button>
      </div>

      {status.kind === "error" && (
        <p className="error">{status.message}</p>
      )}

      {status.kind === "done" && (
        <div className="result">
          <audio src={status.blobUrl} controls />
          <button type="button" onClick={handleSave}>
            保存到...
          </button>
          {savedMsg && <p className="hint">{savedMsg}</p>}
        </div>
      )}
    </section>
  );
}
```

- [ ] **Step 2: Type-check**

```bash
cd D:/code/tts-work/frontend && npx tsc --noEmit 2>&1 | tail -10
```

Expected: no errors. Common pitfalls:
- `verbatimModuleSyntax`: ensure type-only imports use `import type`
- Unused imports: remove them

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ClonePage.tsx
git commit -m "feat(frontend): add ClonePage main UI

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 12: frontend App.tsx — render ClonePage when ready

**Files:**
- Modify: `frontend/src/App.tsx` (line 63-67 ready block + line 2 import)

- [ ] **Step 1: Import ClonePage**

Edit `frontend/src/App.tsx` line 2. Change:

```tsx
import { ApiError, getHealth } from "./api";
import type { HealthResponse } from "./api";
```

to:

```tsx
import { ApiError, getHealth } from "./api";
import type { HealthResponse } from "./api";
import ClonePage from "./pages/ClonePage";
```

- [ ] **Step 2: Render ClonePage in ready view**

Edit `frontend/src/App.tsx`. Replace the ready-view block (lines 63-67):

```tsx
      {view.kind === "ready" && (
        <p className="status ready">
          ✓ 就绪 · GPU: {view.gpu ?? "未知"} · 模型: {view.model}
        </p>
      )}
```

with:

```tsx
      {view.kind === "ready" && (
        <>
          <p className="status ready">
            ✓ 就绪 · GPU: {view.gpu ?? "未知"} · 模型: {view.model}
          </p>
          <ClonePage />
        </>
      )}
```

- [ ] **Step 3: Type-check + dev build**

```bash
cd D:/code/tts-work/frontend && npx tsc --noEmit 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat(frontend): render ClonePage when backend ready

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 13: spec/requirements.md — revise parameter clause

**Files:**
- Modify: `spec/requirements.md` (line 44, non-goal about parameter panel)

- [ ] **Step 1: Update the parameter non-goal**

Edit `spec/requirements.md`. Replace the line:

```
- 参数调节面板（用默认 num_steps=10, guidance=1.0, language=ZH/none, seed=42）
```

with:

```
- 参数调节面板（仅暴露 num_steps / guidance_scale / language 三项，默认 num_steps=10, guidance_scale=1.2, language=zh；不暴露 speaker_scale / ode_method / template / seed 等其他参数；去掉 seed 概念，dots.tts API 不支持且 ODE 求解本不可严格复现） `[v0.1 修订：取代原"用默认 num_steps=10, guidance=1.0, language=ZH/none, seed=42"，由 single-continuation-clone 变更同步]`
```

- [ ] **Step 2: Commit**

```bash
git add spec/requirements.md
git commit -m "docs(spec): revise parameter non-goal per clone task

去掉 seed 概念（dots.tts API 不支持），guidance 1.0→1.2 与 dots.tts
默认对齐，language 固定 zh（高级面板可切 none）。

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 14: End-to-end verification

**Files:**
- No file changes — verification only.

- [ ] **Step 1: Start backend in WSL2 (terminal 1)**

```bash
wsl -d Ubuntu-24.04 -- bash /mnt/d/code/tts-work/scripts/wsl_run_backend.sh
```

Wait until log shows `Application startup complete` and `dots.tts model ready`. (Model already cached, should be fast — ~30s.)

- [ ] **Step 2: Verify backend /api/clone via curl with sample audio**

First, generate or grab a short sample audio in WSL2 view. If you don't have one, synthesize a 3-second sine wave:

```bash
wsl -d Ubuntu-24.04 -- bash -c "source ~/miniconda3/etc/profile.d/conda.sh && conda activate dots_tts && python -c \"
import numpy as np, soundfile as sf
sr = 48000
t = np.linspace(0, 3, sr * 3, endpoint=False)
audio = 0.2 * np.sin(2 * np.pi * 220 * t)
sf.write('/tmp/sine.wav', audio, sr)
print('wrote /tmp/sine.wav')
\""
```

(注意：正弦波不是真实语音，dots.tts 在没真实语音时可能报错或产出异常。如果有真实短中文 wav 文件最好放到 `D:\audio\` 之类，用其 WSL2 路径替换。如果只能用 sine，可跳过此步直接进 Step 3 UI 验证。)

Then curl:
```bash
curl -s -o /tmp/test_clone.wav -w "HTTP %{http_code} size=%{size_download}\n" \
  -X POST http://127.0.0.1:8765/api/clone \
  -H "Content-Type: application/json" \
  -d '{"text":"你好世界","prompt_audio_path":"/tmp/sine.wav","prompt_text":"啊","num_steps":10,"guidance_scale":1.2,"language":"zh"}'
```

Expected: `HTTP 200 size=<some bytes>` (size 100KB-1MB). If sine wave doesn't work for clone, expect `HTTP 413` or `HTTP 500` with detail — that's OK, the endpoint exists and routes correctly.

Verify error cases:
```bash
# 422 empty text
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST http://127.0.0.1:8765/api/clone \
  -H "Content-Type: application/json" \
  -d '{"text":"","prompt_audio_path":"/tmp/sine.wav","prompt_text":"x"}'

# 400 missing file
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST http://127.0.0.1:8765/api/clone \
  -H "Content-Type: application/json" \
  -d '{"text":"x","prompt_audio_path":"/mnt/d/nonexistent.wav","prompt_text":"x"}'
```

Expected: `HTTP 422` and `HTTP 400` respectively.

- [ ] **Step 3: Start Tauri dev (terminal 2)**

```bash
export PATH="/c/Program Files (x86)/nvm/v24.15.0:$PATH"
export HTTP_PROXY= && export HTTPS_PROXY=
cd D:/code/tts-work && tauri dev
```

Wait until Tauri window opens. Frontend polls `/api/health`; once ready, the ClonePage UI renders under the status line.

- [ ] **Step 4: Manual UI verification**

In the Tauri window:
1. Click "选择文件" → pick a real short Chinese wav (e.g. a 3-second recording of yourself saying one sentence)
2. Type the transcript in "参考转录"
3. Type target text in "目标文本"
4. Click "合成" → wait for `<audio>` to appear (10-30s)
5. Click play on `<audio>` → should hear synthesized voice
6. Click "保存到..." → pick a folder (e.g. `D:\out\`) → type filename → confirm
7. Verify the file exists at the saved path

If any step fails:
- Check browser devtools (right-click → inspect) for console errors
- Check backend stdout (terminal 1) for stack traces
- File an issue in `openspec/changes/single-continuation-clone/` notes (don't move to archive yet)

- [ ] **Step 5: No commit needed — verification only**

If everything passed, proceed to archive (`/opsx:archive`). If issues found, file as new tasks or fix in-place before archiving.

---

## Self-Review Summary

**Spec coverage check** (against `specs/synthesis/spec.md` scenarios):
- 完整单段克隆流程 → Tasks 2, 3, 11, 14 ✓
- 高级参数覆盖默认值 → Tasks 2 (defaults), 10 (UI), 11 (wiring) ✓
- 保存到指定位置 → Task 11 `handleSave` ✓
- 参考音频路径无效 → Task 1 (win_to_wsl2 raises), Task 11 (try/catch) ✓
- 文件不存在/不可读 → Task 1 (`validate_prompt_audio`), Task 2 (HTTPException 400) ✓
- 文本/转录为空 → Task 2 (HTTPException 422), Task 11 (canSynth disables button) ✓
- 文本过长 max_generate_length → Task 2 (HTTPException 413) ✓
- dots.tts 合成失败 → Task 2 (HTTPException 500) ✓
- 后端未就绪 → Task 12 (ClonePage only renders in ready view) ✓
- 网络错误 → Task 9 (ApiError network), Task 11 (handles) ✓
- 模型常驻复用 → existing `backend/runtime.py` singleton ✓
- 路径转换规则 → Tasks 1 + 8 (mirror implementations) ✓

**Placeholder scan**: none.

**Type consistency**:
- `AdvancedParamValues.numSteps` ↔ `CloneParams.numSteps` (camelCase, both) ✓
- `CloneLanguage = "zh" | "none"` ↔ backend `language: str = Field(..., pattern="^(zh|none)$")` ✓
- `synthesize_clone` signature ↔ `clone_route` call ✓

All consistent. Plan ready.
