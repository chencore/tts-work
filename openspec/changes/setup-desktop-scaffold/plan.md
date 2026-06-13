# setup-desktop-scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 v0.1 桌面应用的技术底盘——Tauri + React + TS 前端 + Python FastAPI 后端 + dots.tts 模型常驻加载，前后端通过本地 HTTP 通信。完成后整个应用骨架可启动，但尚无 TTS 合成功能。

**Architecture:** Python FastAPI 后端启动时同步加载 dots.tts 模型并常驻 GPU，暴露 `/api/health` 让前端轮询状态。React 前端通过 fetch 调本地 127.0.0.1:8765。Tauri 壳只负责装窗口。dev 模式下 Python 和 Tauri 分别在两个终端启动。

**Tech Stack:** Tauri 2.x · React 18 + Vite 5 + TypeScript 5 · Python 3.10 (conda env `dots_tts`) · FastAPI + Uvicorn · dots_tts (from git) · PyTorch with CUDA

**Spec reference:** [openspec/changes/setup-desktop-scaffold/design.md](design.md)

---

## File Structure

| 文件 | 职责 |
|------|------|
| `.gitignore` | 忽略 Python/Node/Rust 产物、模型权重缓存 |
| `backend/__init__.py` | 标记 backend 为 Python package |
| `backend/requirements.txt` | Python 依赖（fastapi、uvicorn、dots_tts from git） |
| `backend/runtime.py` | dots.tts 模型单例：同步加载、状态机、`get_runtime()` |
| `backend/app.py` | FastAPI 实例 + `/api/health` + 端口环境变量 |
| `frontend/package.json` | npm 依赖与脚本（由 Vite 模板生成） |
| `frontend/vite.config.ts` | Vite 配置（由模板生成 + 微调） |
| `frontend/index.html` | Vite 入口 HTML（由模板生成） |
| `frontend/src/main.tsx` | React 入口（由模板生成） |
| `frontend/src/api.ts` | HTTP 客户端 + 错误类型 |
| `frontend/src/App.tsx` | 主页：轮询 `/api/health` 显示四态 |
| `src-tauri/Cargo.toml` | Rust 依赖（由 `cargo tauri init` 生成） |
| `src-tauri/tauri.conf.json` | Tauri 配置（devUrl、frontendDist、allowlist） |
| `src-tauri/src/main.rs` | Tauri 入口（默认即可） |
| `src-tauri/icons/` | 应用图标（由模板生成，占位即可） |
| `README.md` | dev 启动文档 + 故障排查（修改现有文件） |

---

## Task 1: 项目目录结构与 .gitignore

**Files:**
- Create: `.gitignore`
- Create: `backend/`, `frontend/`, `src-tauri/` 目录（空目录占位）

- [ ] **Step 1: 检查当前目录结构**

Run: `ls -la`
Expected output: 看到 `spec/`、`openspec/`、`docs/`、`CLAUDE.md`、`README.md`、`LICENSE` 等已有内容，无 `backend/`、`frontend/`、`src-tauri/`。

- [ ] **Step 2: 创建空目录占位**

Run:
```bash
mkdir -p backend frontend src-tauri
touch backend/.gitkeep frontend/.gitkeep src-tauri/.gitkeep
```

- [ ] **Step 3: 写 `.gitignore`**

Create `.gitignore` with content:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
env/
*.egg-info/
.pytest_cache/

# Model weights cache (HuggingFace)
.cache/
models/

# Node / Vite
node_modules/
frontend/dist/
*.log
npm-debug.log*

# Rust / Tauri
src-tauri/target/
src-tauri/Cargo.lock
src-tauri/binaries/backend*

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 4: 提交**

```bash
git add .gitignore backend/.gitkeep frontend/.gitkeep src-tauri/.gitkeep
git commit -m "chore: scaffold project directories and .gitignore"
```

---

## Task 2: Python 后端依赖清单

**Files:**
- Create: `backend/__init__.py`
- Create: `backend/requirements.txt`
- Delete: `backend/.gitkeep`（被实际文件取代）

- [ ] **Step 1: 写 `backend/__init__.py`**

Create `backend/__init__.py` with content:

```python
"""dots.tts desktop app — backend package."""
```

- [ ] **Step 2: 写 `backend/requirements.txt`**

Create `backend/requirements.txt` with content:

```text
# Web framework
fastapi>=0.110,<1.0
uvicorn[standard]>=0.27,<1.0

# dots.tts (installed from GitHub source with constraints from the same repo)
dots-tts @ git+https://github.com/rednote-hilab/dots.tts.git@main

# Note: torch / CUDA version is pinned by dots.tts's constraints/recommended.txt
# Install command (see README):
#   pip install -r backend/requirements.txt \
#     -c https://raw.githubusercontent.com/rednote-hilab/dots.tts/main/constraints/recommended.txt
```

- [ ] **Step 3: 删除占位文件**

Run: `git rm backend/.gitkeep`

- [ ] **Step 4: 提交**

```bash
git add backend/__init__.py backend/requirements.txt
git commit -m "feat(backend): add package init and requirements.txt"
```

> **说明：** 本任务**不**实际 `pip install`——conda env 创建和依赖安装放在 Task 5 的端到端验证步骤里，因为安装耗时较长（torch + CUDA 几个 GB），且需要 conda 环境。

---

## Task 3: dots.tts 模型单例（`backend/runtime.py`）

**Files:**
- Create: `backend/runtime.py`

- [ ] **Step 1: 写 `backend/runtime.py`**

Create `backend/runtime.py` with content:

```python
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
        _RUNTIME = DotsTtsRuntime.from_pretrained(
            _STATE.model_name,
            precision="bfloat16",
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
```

- [ ] **Step 2: 提交**

```bash
git add backend/runtime.py
git commit -m "feat(backend): add dots.tts runtime singleton with state machine"
```

---

## Task 4: FastAPI 入口与 `/api/health`（`backend/app.py`）

**Files:**
- Create: `backend/app.py`

- [ ] **Step 1: 写 `backend/app.py`**

Create `backend/app.py` with content:

```python
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
```

- [ ] **Step 2: 提交**

```bash
git add backend/app.py
git commit -m "feat(backend): add FastAPI app with /api/health endpoint"
```

---

## Task 5: 后端独立验证（含 conda env 创建）

**Files:**
- Modify: `README.md`（提前在 README 里写 dev 启动说明，本任务用于对照执行）

> 本任务**不**改代码文件，只跑命令验证 Task 2-4 的产物。但需要先把 dev 启动文档写到 README——所以提前做 Task 10 的部分内容。

- [ ] **Step 1: 创建 conda env 并安装依赖**

Run:
```bash
conda create -n dots_tts python=3.10 -y
conda activate dots_tts
python -m pip install --upgrade pip
pip install -r backend/requirements.txt \
  -c https://raw.githubusercontent.com/rednote-hilab/dots.tts/main/constraints/recommended.txt
```

Expected: 安装成功，无错误。首次会下载 PyTorch + CUDA wheels（数 GB）+ dots.tts 源码，可能耗时 5-15 分钟。

- [ ] **Step 2: 验证 torch+CUDA 可用**

Run:
```bash
conda activate dots_tts
python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

Expected: 输出形如 `2.x.x True NVIDIA GeForce RTX ...`。若 `cuda.is_available()` 为 `False`，**停下来排查**——常见原因：CUDA toolkit 版本与 PyTorch wheel 不匹配、NVIDIA 驱动过旧。

- [ ] **Step 3: 启动后端**

Run:
```bash
conda activate dots_tts
python -m backend.app
```

Expected 输出（首次启动）：
```
[INFO] backend.runtime: GPU detected: NVIDIA GeForce RTX ...
[INFO] backend.runtime: Loading dots.tts model: rednote-hilab/dots.tts-base
Downloading: 100% ... (HF 下载进度，首次会下 ~5GB)
[INFO] backend.runtime: dots.tts model ready (loaded in XX.Xs)
[INFO] backend.app: Starting backend on http://127.0.0.1:8765
INFO:     Uvicorn running on http://127.0.0.1:8765
```

> **如果 HF 下载太慢：** Ctrl+C 停止，设置镜像后重试：
> ```bash
> # Windows PowerShell
> set HF_ENDPOINT=https://hf-mirror.com
> # bash
> export HF_ENDPOINT=https://hf-mirror.com
> ```

- [ ] **Step 4: 另开终端 curl `/api/health`**

Run:
```bash
curl http://127.0.0.1:8765/api/health
```

Expected（模型加载完成后）：
```json
{"status":"ready","model":"rednote-hilab/dots.tts-base","gpu":"NVIDIA GeForce RTX ...","elapsed_ms":12345,"error":null}
```

也验证 `/docs`：在浏览器打开 `http://127.0.0.1:8765/docs`，应看到 FastAPI 自动生成的 Swagger 页面，含 `/api/health`。

- [ ] **Step 5: 验证模型单例（多次请求不重载）**

连续 curl 三次：
```bash
curl http://127.0.0.1:8765/api/health
curl http://127.0.0.1:8765/api/health
curl http://127.0.0.1:8765/api/health
```

Expected: 三次返回的 `elapsed_ms` 都很接近（差值 < 100ms），说明模型只在进程启动时加载一次，请求不触发重载。

- [ ] **Step 6: 停止后端**

在后端终端按 Ctrl+C，确认进程退出。

- [ ] **Step 7: 无代码改动，跳过 commit**

---

## Task 6: React + Vite + TS 前端骨架

**Files:**
- Create: `frontend/package.json`、`frontend/vite.config.ts`、`frontend/index.html`、`frontend/tsconfig.json`、`frontend/src/main.tsx`、`frontend/src/App.tsx`（先占位，Task 8 改）、`frontend/src/index.css` 等（Vite 模板生成）
- Delete: `frontend/.gitkeep`

- [ ] **Step 1: 进入 frontend 目录用 Vite 模板初始化**

Run:
```bash
cd frontend
npm create vite@latest . -- --template react-ts
```

如果提示目录非空（因为 `.gitkeep`），先 `rm .gitkeep` 再重试。

按提示完成（Vite 6+ 会问 "Install dependencies?"，选 No——下一步手动装）。

- [ ] **Step 2: 安装依赖**

Run:
```bash
cd frontend
npm install
```

Expected: `node_modules/` 创建，无错误。

- [ ] **Step 3: 验证 Vite dev server 启动**

Run:
```bash
cd frontend
npm run dev
```

Expected: 终端输出 `VITE v6.x.x ready in XXX ms` 与 `Local: http://localhost:5173/`。浏览器打开 5173 端口看到默认 React 欢迎页。Ctrl+C 停止。

- [ ] **Step 4: 删除占位文件**

Run: `git rm -f frontend/.gitkeep` （如果该文件还在）

- [ ] **Step 5: 提交（注意忽略 node_modules）**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold React + Vite + TypeScript"
```

---

## Task 7: 前端 HTTP 客户端（`frontend/src/api.ts`）

**Files:**
- Create: `frontend/src/api.ts`

- [ ] **Step 1: 写 `frontend/src/api.ts`**

Create `frontend/src/api.ts` with content:

```typescript
const API_BASE =
  import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8765";

export type HealthStatus = "loading" | "ready" | "error";

export interface HealthResponse {
  status: HealthStatus;
  model: string;
  gpu: string | null;
  elapsed_ms: number;
  error: string | null;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly kind: "network" | "http" | "parse",
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function getHealth(): Promise<HealthResponse> {
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}/api/health`);
  } catch (e) {
    throw new ApiError(
      e instanceof Error ? e.message : "network error",
      "network",
    );
  }
  if (!resp.ok) {
    throw new ApiError(`HTTP ${resp.status}`, "http");
  }
  try {
    return (await resp.json()) as HealthResponse;
  } catch (e) {
    throw new ApiError(
      e instanceof Error ? e.message : "parse error",
      "parse",
    );
  }
}
```

- [ ] **Step 2: 提交**

```bash
git add frontend/src/api.ts
git commit -m "feat(frontend): add HTTP client with typed health endpoint"
```

---

## Task 8: 前端状态展示 UI（`frontend/src/App.tsx`）

**Files:**
- Modify: `frontend/src/App.tsx`（替换 Vite 模板默认内容）
- Modify: `frontend/src/index.css` 或 `frontend/src/App.css`（替换为极简样式）

- [ ] **Step 1: 替换 `frontend/src/App.tsx`**

Replace entire content of `frontend/src/App.tsx` with:

```tsx
import { useEffect, useState } from "react";
import { ApiError, getHealth, HealthResponse } from "./api";

type View =
  | { kind: "waiting" }
  | { kind: "loading"; elapsedMs: number }
  | { kind: "ready"; gpu: string | null; model: string }
  | { kind: "error"; message: string };

function fromHealth(h: HealthResponse): View {
  if (h.status === "ready") {
    return { kind: "ready", gpu: h.gpu, model: h.model };
  }
  if (h.status === "error") {
    return { kind: "error", message: h.error ?? "unknown error" };
  }
  return { kind: "loading", elapsedMs: h.elapsed_ms };
}

function fromError(e: unknown): View {
  if (e instanceof ApiError && e.kind === "network") {
    return { kind: "waiting" };
  }
  return {
    kind: "error",
    message: e instanceof Error ? e.message : String(e),
  };
}

export default function App() {
  const [view, setView] = useState<View>({ kind: "waiting" });

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const h = await getHealth();
        if (!cancelled) setView(fromHealth(h));
      } catch (e) {
        if (!cancelled) setView(fromError(e));
      }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <main className="app">
      <h1>tts-work</h1>
      {view.kind === "waiting" && (
        <p className="status waiting">等待后端启动...</p>
      )}
      {view.kind === "loading" && (
        <p className="status loading">
          模型加载中（{(view.elapsedMs / 1000).toFixed(1)}s）
        </p>
      )}
      {view.kind === "ready" && (
        <p className="status ready">
          ✓ 就绪 · GPU: {view.gpu ?? "未知"} · 模型: {view.model}
        </p>
      )}
      {view.kind === "error" && (
        <p className="status error">后端错误：{view.message}</p>
      )}
    </main>
  );
}
```

- [ ] **Step 2: 替换 `frontend/src/index.css`（或 `App.css`）**

Replace entire content of `frontend/src/index.css` with:

```css
:root {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
    "Microsoft YaHei", sans-serif;
  color: #222;
  background: #f7f7f8;
}
body {
  margin: 0;
}
.app {
  max-width: 640px;
  margin: 80px auto;
  padding: 32px;
  text-align: center;
}
.app h1 {
  font-size: 28px;
  margin-bottom: 24px;
}
.status {
  font-size: 18px;
  padding: 16px;
  border-radius: 8px;
  display: inline-block;
}
.status.waiting {
  color: #888;
  background: #eee;
}
.status.loading {
  color: #0066cc;
  background: #e6f0ff;
}
.status.ready {
  color: #1a7f37;
  background: #e6f4ea;
}
.status.error {
  color: #cc0000;
  background: #ffe6e6;
}
```

如果 `App.css` 存在并从 `App.tsx` import，删掉那个 import 行。

- [ ] **Step 3: 删除模板多余文件**

Run:
```bash
cd frontend
rm -f src/App.css src/assets/react.svg public/vite.svg 2>/dev/null
```

如果 `App.tsx` 里有 `import './App.css'` 之类的行，确保已删除。

- [ ] **Step 4: TypeScript 编译检查**

Run:
```bash
cd frontend
npm run build
```

Expected: `tsc` 无错误，`dist/` 生成。

- [ ] **Step 5: 手动验证 UI**

启动后端（Task 5 步骤 3 的命令），再启动前端：
```bash
cd frontend
npm run dev
```

打开 `http://localhost:5173`，预期看到：
- 后端未启动时：显示 "等待后端启动..."
- 后端启动但模型还在加载：显示 "模型加载中（X.Xs）"，秒数递增
- 模型加载完成：显示 "✓ 就绪 · GPU: ... · 模型: rednote-hilab/dots.tts-base"
- 停掉后端：1 秒内回到 "等待后端启动..."

Ctrl+C 停止两个终端。

- [ ] **Step 6: 提交**

```bash
git add frontend/src/App.tsx frontend/src/index.css frontend/src/assets/ frontend/public/
git commit -m "feat(frontend): add health-polling status UI"
```

（如果 `frontend/src/assets/` 已空，可 `git rm -r` 掉。）

---

## Task 9: Tauri 2.x 项目初始化与配置

**Files:**
- Create: `src-tauri/Cargo.toml`、`src-tauri/tauri.conf.json`、`src-tauri/src/main.rs`、`src-tauri/src/lib.rs`、`src-tauri/build.rs`、`src-tauri/icons/`、`src-tauri/capabilities/default.json`（由 `cargo tauri init` 生成）
- Delete: `src-tauri/.gitkeep`

- [ ] **Step 1: 检查 Rust 工具链**

Run:
```bash
cargo --version
rustc --version
```

Expected: 输出 Rust 版本号。如果未安装，去 https://tauri.app/start/prerequisites/ 按指引装 Rust + WebView2（Windows 已预装）。

- [ ] **Step 2: 在项目根用 `cargo tauri init` 初始化**

如果 `cargo tauri` 子命令不可用，先装 CLI：
```bash
cargo install tauri-cli --version "^2.0"
```

然后初始化：
```bash
cargo tauri init
```

交互式提示按以下选择：
- `App name` → `tts-work`
- `Window title` → `tts-work`
- `Web assets location` → `../frontend/dist`
- `Dev server URL` → `http://localhost:5173`
- `Frontend dev command` → `npm run dev`
- `Frontend build command` → `npm run build`
- 其他用默认

> **注意：** `cargo tauri init` 在哪个目录运行就在哪生成 `src-tauri/`。要在**项目根**运行，让它把 `src-tauri/` 生成在项目根下。我们 Task 1 已经创建了空的 `src-tauri/` 目录，需要先删了再 init：
> ```bash
> rmdir src-tauri  # 或 rm -rf src-tauri（如果只有 .gitkeep）
> cargo tauri init
> ```

- [ ] **Step 3: 编辑 `src-tauri/tauri.conf.json`**

打开 `src-tauri/tauri.conf.json`，找到 `app.security.csp` 或 `app.windows[0]` 等字段，确认或调整为：

```json
{
  "$schema": "https://schema.tauri.app/config/2",
  "productName": "tts-work",
  "version": "0.1.0",
  "identifier": "com.ck.ttswork",
  "build": {
    "frontendDist": "../frontend/dist",
    "devUrl": "http://localhost:5173",
    "beforeDevCommand": "cd ../frontend && npm run dev",
    "beforeBuildCommand": "cd ../frontend && npm run build"
  },
  "app": {
    "windows": [
      {
        "title": "tts-work",
        "width": 800,
        "height": 600
      }
    ],
    "security": {
      "csp": null
    }
  },
  "bundle": {
    "active": true,
    "targets": "all",
    "icon": [
      "icons/32x32.png",
      "icons/128x128.png",
      "icons/128x128@2x.png",
      "icons/icon.icns",
      "icons/icon.ico"
    ]
  }
}
```

> 字段顺序、补全字段以 `cargo tauri init` 生成的内容为准——上面只列关键改动。**不要全量覆盖**，只改需要改的字段。

- [ ] **Step 4: 配置 HTTP allowlist（Tauri 2 capabilities）**

打开 `src-tauri/capabilities/default.json`，改为：

```json
{
  "$schema": "../gen/schemas/desktop-schema.json",
  "identifier": "default",
  "description": "Capability for the main window",
  "windows": ["main"],
  "permissions": [
    "core:default",
    {
      "identifier": "http:default",
      "allow": [
        { "url": "http://127.0.0.1:8765" },
        { "url": "http://127.0.0.1:8765/*" },
        { "url": "http://localhost:*" }
      ]
    }
  ]
}
```

- [ ] **Step 5: 删除占位文件**

Run: `git rm -f src-tauri/.gitkeep 2>/dev/null || true`

- [ ] **Step 6: 验证 `cargo tauri dev` 能启动**

Run（项目根）:
```bash
cargo tauri dev
```

首次会编译 Rust，可能耗时几分钟。完成后预期：
- 自动启动 Vite dev server（看到 Vite 日志）
- 弹出桌面窗口
- 窗口里显示前端 UI（如果后端没起，显示 "等待后端启动..."；如果后端起着，显示加载/就绪状态）

Ctrl+C 停止。

> **如果端口 5173 已被占用**（你之前手动起的 Vite 还没关）：先关掉再重试。

- [ ] **Step 7: 提交**

```bash
git add src-tauri/
git commit -m "feat(tauri): init Tauri 2.x shell with HTTP allowlist"
```

---

## Task 10: README dev 启动文档

**Files:**
- Modify: `README.md`（在现有模板内容后追加 dev 启动章节，**不要删除原有内容**）

- [ ] **Step 1: 读现有 README**

Run: 读 `README.md`，找到合适插入位置（一般在 "使用方式" 或 "Quick Start" 章节，如果没有就在最末追加）。

- [ ] **Step 2: 追加 dev 启动章节**

在 README 末尾（或合适的章节）追加：

```markdown
## 开发指南（v0.1）

### 一次性环境准备

**1. 创建 conda 环境（Python 3.10）：**

```bash
conda create -n dots_tts python=3.10 -y
conda activate dots_tts
python -m pip install --upgrade pip
```

**2. 安装 Python 后端依赖：**

```bash
pip install -r backend/requirements.txt \
  -c https://raw.githubusercontent.com/rednote-hilab/dots.tts/main/constraints/recommended.txt
```

> 首次会下载 PyTorch + CUDA wheels（数 GB），耗时 5-15 分钟。

**3. 验证 CUDA 可用：**

```bash
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

如果输出 `False`，先排查 CUDA / 驱动问题再继续。

**4. 安装前端依赖：**

```bash
cd frontend
npm install
```

**5. 验证 Rust 工具链（Tauri 需要）：**

```bash
cargo --version
```

未安装参考 https://tauri.app/start/prerequisites/ 。

### 日常开发（两个终端）

**终端 1 — Python 后端：**

```bash
conda activate dots_tts
python -m backend.app
```

后端启动时会同步加载 dots.tts 模型（首次需从 HuggingFace 下载 ~5GB）。加载完成后 `http://127.0.0.1:8765/api/health` 返回 `status=ready`。

**终端 2 — Tauri 桌面壳（自动拉起 Vite）：**

```bash
cargo tauri dev
```

弹出桌面窗口，前端每秒轮询 `/api/health` 显示状态。

### 故障排查

**HF 模型下载太慢：** 设置镜像：
```bash
# Windows PowerShell
set HF_ENDPOINT=https://hf-mirror.com
# bash
export HF_ENDPOINT=https://hf-mirror.com
```

**端口 8765 被占用：** 改环境变量：
```bash
# PowerShell
set TTS_PORT=8766
# bash
export TTS_PORT=8766
```
（注意：前端默认连 8765，改后端端口后需在 `frontend/.env` 里设 `VITE_API_BASE=http://127.0.0.1:8766`。）

**`cargo tauri dev` 报 5173 占用：** 之前的 Vite 没关干净。关掉所有 node 进程或重启。
```

- [ ] **Step 3: 提交**

```bash
git add README.md
git commit -m "docs(readme): add v0.1 dev setup guide"
```

---

## Task 11: 端到端验证与收尾

**Files:** 无新文件

- [ ] **Step 1: 全新环境跑通**

关闭所有相关终端，按 README 的"日常开发"章节从零起一遍：

```bash
# T1
conda activate dots_tts
python -m backend.app
# 等 /api/health 返回 ready
```

```bash
# T2
cargo tauri dev
```

- [ ] **Step 2: 验证四个状态视图**

在 Tauri 窗口里依次验证：
1. **等待视图**：先启动 Tauri、后端没起 → 看到 "等待后端启动..."
2. **加载视图**：起后端 → 看到 "模型加载中（X.Xs）"，秒数递增
3. **就绪视图**：模型加载完成 → 看到 "✓ 就绪 · GPU: ... · 模型: rednote-hilab/dots.tts-base"
4. **错误视图**：起后端但故意配错环境变量 `DOTS_TTS_MODEL=nonexistent/repo` → 看到 "后端错误：..."

- [ ] **Step 3: 验证模型常驻**

就绪状态下，关闭 Tauri 窗口再开（`cargo tauri dev` 再次运行），后端**不重启**。`/api/health` 的 `elapsed_ms` 应保持原值（不重置为 0）。

- [ ] **Step 4: 检查 git 状态**

Run:
```bash
git status
git log --oneline -20
```

Expected: 工作树干净；最近 10+ 条 commit 都是本任务产物。

- [ ] **Step 5: 推送 feature 分支（可选）**

```bash
git push -u origin feature/setup-desktop-scaffold
```

> 推送前请用户确认。

- [ ] **Step 6: 通知归档**

向用户报告：
> setup-desktop-scaffold 任务全部完成，11 个 task 全过。下一步可以 `/opsx:archive` 归档本变更并合并回 `version/v0.1`。

---

## 完成后

执行 `/opsx:archive` 归档本变更。归档时 AI 会：
1. 把 `openspec/changes/setup-desktop-scaffold/` 移到 `archive/`
2. 在 `spec/tasks.md` 勾选 setup-desktop-scaffold
3. 提请人工确认是否把 `design.md §7` 列的两条待定项（桌面壳技术栈 / 通信方式）提升到 `spec/design.md`
4. 追加 `spec/devlog.md` 一条
