# Design: setup-desktop-scaffold

## 1. 技术选型（决策结果）

| 维度 | 选择 | 备选放弃 | 理由 |
|------|------|----------|------|
| 桌面壳 | Tauri 2.x | Electron（重 150MB+）/ PyWebView（生态小） | 体积小、性能好、Rust 壳稳定 |
| 前端框架 | React + Vite + TS | Vue / Svelte | Tauri 官方默认模板、生态最大 |
| 前后端通信 | 本地 HTTP (FastAPI) | stdio JSON-RPC / Tauri events | 可 curl 调试、FastAPI `/docs` 免费、与 Tauri 解耦 |
| Python 环境 | conda env `dots_tts` (Python 3.10) | base 3.12 / uv | 与 dots.tts 官方一致，避免版本不兼容 |
| 端口 | 固定 `127.0.0.1:8765` | 动态扫描 | 个人单用户场景，冲突时改环境变量 `TTS_PORT` |

## 2. 项目结构

```
<project-root>/
├── src-tauri/                # Tauri Rust 壳
│   ├── src/main.rs
│   ├── tauri.conf.json
│   ├── Cargo.toml
│   ├── icons/
│   └── binaries/             # PyInstaller 产物占位，本任务留空
├── frontend/                 # React + Vite + TS
│   ├── src/
│   │   ├── App.tsx           # 主页：轮询 /api/health 显示状态
│   │   ├── api.ts            # HTTP 客户端
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── backend/                  # Python FastAPI
│   ├── __init__.py
│   ├── app.py                # FastAPI 入口
│   ├── runtime.py            # dots.tts 加载（singleton）
│   └── requirements.txt
└── ...
```

## 3. 模块设计

### `backend/runtime.py` — 模型单例

- 模块导入时**同步**调用 `DotsTtsRuntime.load_pretrained()` 加载模型，可能耗时 10–30s（首次还需下载 ~5GB 权重）
- 模块级状态：`_runtime`、`_status`（`loading` / `ready` / `error`）、`_load_started_at`、`_error_msg`
- `get_runtime()` 返回当前 runtime；若 `status != ready` 抛 `RuntimeError`

**关键决策：模块导入时同步加载 vs 懒加载**

- 选同步：FastAPI 启动即触发，前端 health 接口能直接反映真实进度
- 不选懒加载：首次合成会卡住 30s，UX 差，且 health 接口无法反映真实状态

### `backend/app.py` — FastAPI 入口

- 监听 `127.0.0.1:8765`（端口可由 `TTS_PORT` 环境变量覆盖）
- 启动时 `import backend.runtime`（触发模型加载）
- `GET /api/health` → `{status, model, gpu, elapsed_ms, error?}`
- CORS 全开（个人本地，无安全顾虑）

### `frontend/src/api.ts` — HTTP 客户端

- `baseURL = http://127.0.0.1:8765`（可被 `import.meta.env.VITE_API_BASE` 覆盖）
- 统一 `request<T>(path)` 函数：fetch + JSON 解析 + 错误抛出
- 网络错误（fetch throw）封装为 `ApiError` 类型供 UI 区分

### `frontend/src/App.tsx` — 状态展示 UI

- `useEffect` 每 1s 轮询 `/api/health`
- 四种视图：
  - **等待后端**（fetch 失败）→ "等待后端启动..."
  - **加载中** → "模型加载中（X 秒）"
  - **就绪** → "✓ 就绪 · GPU: <name>"
  - **错误** → "后端错误：<msg>"
- 极简，无路由、无状态管理库

### `src-tauri/tauri.conf.json` — Tauri 配置

- `build.frontendDist`: `../frontend/dist`
- `build.devUrl`: `http://localhost:5173`
- `build.beforeDevCommand`: `cd ../frontend && npm run dev`
- `build.beforeBuildCommand`: `cd ../frontend && npm run build`
- allowlist：`http` 允许 `http://127.0.0.1:8765`；`shell` 关闭
- 本任务**不**配 sidecar / `externalBin`（PyInstaller 留给 package-release）

## 4. dev 工作流

```bash
# 一次性环境准备
conda create -n dots_tts python=3.10 -y
conda activate dots_tts
pip install -r backend/requirements.txt \
  -c https://raw.githubusercontent.com/rednote-hilab/dots.tts/main/requirements/constraints.txt
cd frontend && npm install

# 日常 dev（两终端）
# T1：Python 后端
conda activate dots_tts && python -m backend.app
# T2：Tauri + Vite
cd src-tauri && cargo tauri dev
```

## 5. 风险与权衡

### 风险 1：dots.tts 在 conda env (Python 3.10) 下能否装上 torch+CUDA

- **缓解**：`requirements.txt` 显式钉版本；首次启动验证 `torch.cuda.is_available()`
- **兜底**：若失败，README 说明走 PyTorch 官网安装命令再装 dots.tts

### 风险 2：模型加载耗时不可控（首次需从 HF 下载 ~5GB）

- **缓解**：`runtime.py` 启动日志打印下载进度；前端 health 在 loading 状态显示 `elapsed_ms` 让用户感知
- **兜底**：README 说明首次启动需等待，HF 下载慢可设 `HF_ENDPOINT=https://hf-mirror.com` 走镜像

### 风险 3：端口 8765 冲突

- **缓解**：FastAPI 启动失败时打印明确错误；`TTS_PORT` 环境变量可改
- 不做动态扫描：单用户场景过度设计

## 6. 待定项（保留到执行期间或后续任务定）

- 模型从 HF vs ModelScope 拉：默认 HF，下载慢可设 `HF_ENDPOINT` 切镜像
- 端口冲突自动处理：本任务用固定端口 + 环境变量；动态扫描留待 `package-release`
- Tauri sidecar 自动 spawn Python：本任务 dev 用两终端手动起；自动化留待 `package-release` 或后续优化任务

## 7. 待提升到 `spec/design.md` 的条目（archive 时处理）

下列 `spec/design.md` §7 的待定项将在本任务归档时提请人工提升：

- ✅ 桌面壳技术栈 → Tauri 2.x
- ✅ 桌面壳 ⇄ Python 后端通信方式 → 本地 HTTP（FastAPI on 127.0.0.1:8765）

剩余待定项保留：音色库存储格式、目标 OS、默认参数具体值。
