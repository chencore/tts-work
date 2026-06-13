# Design: setup-desktop-scaffold

## 1. 技术选型（决策结果）

| 维度 | 选择 | 备选放弃 | 理由 |
|------|------|----------|------|
| 桌面壳 | Tauri 2.x | Electron（重 150MB+）/ PyWebView（生态小） | 体积小、性能好、Rust 壳稳定 |
| 前端框架 | React + Vite + TS | Vue / Svelte | Tauri 官方默认模板、生态最大 |
| 前后端通信 | 本地 HTTP (FastAPI) | stdio JSON-RPC / Tauri events | 可 curl 调试、FastAPI `/docs` 免费、与 Tauri 解耦 |
| **Python 运行环境** | **WSL2 Ubuntu-24.04 + conda env `dots_tts` (Python 3.10)** | 原生 Windows conda（pynini 装不上）/ Docker | dots.tts 通过 WeTextProcessing 依赖 pynini，PyPI 无 Windows wheel；WSL2 与官方 Linux 平台一致，最少踩坑 |
| 端口 | 固定 `127.0.0.1:8765` | 动态扫描 | 个人单用户场景，冲突时改环境变量 `TTS_PORT` |

### 关键架构决策：WSL2 而非原生 Windows

dots.tts 通过 `WeTextProcessing → pynini` 依赖 OpenFst 的 Python 绑定。pynini 在 PyPI 上**只有源码包**，构建时用 GCC/Clang flag（`-Wno-register`），MSVC 不识别，**原生 Windows 装不上**。WSL2 提供原生 Linux 环境绕过该问题，同时 NVIDIA 为 WSL2 提供 CUDA 驱动支持，GPU 性能与原生接近。

**影响：**

- Python 后端进程跑在 WSL2，Tauri 壳跑在 Windows 主机
- 两者通过 `127.0.0.1:8765` 通信（WSL2 默认 localhost 双向转发到 Windows 主机）
- 项目代码继续放 Windows 文件系统（`D:\code\tts-work`），WSL2 通过 `/mnt/d/code/tts-work` 访问——文件可被两端工具读写
- 模型权重缓存走 WSL2 用户 home（`~/.cache/huggingface`），Linux 文件系统下 IO 快

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

**一次性准备：**

1. Windows 上：clone 项目 (`D:\code\tts-work`)；clone dots.tts 源码 (`D:\code\dots.tts`)；装好 Node.js、Rust、Tauri CLI
2. WSL2 Ubuntu-24.04：跑 `scripts/wsl_install_conda.sh` 装 miniconda；跑 `scripts/wsl_install_dotstts.sh` 创建 `dots_tts` conda env 并装好所有 Python 依赖

**日常 dev（两个终端，分属 Windows / WSL2）：**

```bash
# 终端 1（WSL2）：Python 后端
wsl -d Ubuntu-24.04
conda activate dots_tts
cd /mnt/d/code/tts-work
python -m backend.app

# 终端 2（Windows PowerShell / bash）：Tauri + Vite
cd D:\code\tts-work
tauri dev
```

WSL2 后端监听 `127.0.0.1:8765`，Windows 上的 Tauri 前端 fetch 这个地址时，WSL2 的 localhost 自动转发到 Windows 主机，所以前端无需任何特殊配置。

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
- Tauri sidecar 自动 spawn Python（在 WSL2 里）：本任务 dev 用两终端手动起；自动化留待 `package-release` 或后续优化任务
- **打包发行方式**：v0.1 最终装到用户机器时，需要自动装 WSL2 + conda env + dots.tts 依赖，或者用 Docker 镜像方案。这部分留待 `package-release` 任务详细设计

## 7. 待提升到 `spec/design.md` 的条目（archive 时处理）

下列 `spec/design.md` §7 的待定项将在本任务归档时提请人工提升：

- ✅ 桌面壳技术栈 → Tauri 2.x
- ✅ 桌面壳 ⇄ Python 后端通信方式 → 本地 HTTP（FastAPI on 127.0.0.1:8765）

剩余待定项保留：音色库存储格式、目标 OS、默认参数具体值。
