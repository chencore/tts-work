# tts-work

> 基于 [dots.tts](https://github.com/rednote-hilab/dots.tts) 的 Windows 桌面语音克隆应用。

---

## 项目简介

`tts-work` 是一个单段语音克隆（Single-Segment Continuation Clone）桌面程序：

- 选择一段参考音频（支持 `wav/mp3/flac/ogg/m4a`）
- 输入参考音频对应的文本
- 输入想要合成的目标文本
- 点击合成，即可生成与参考音色相似的新音频

前端为 Tauri 2.x + React + TypeScript 桌面应用；后端为 Python FastAPI，跑在 WSL2 Ubuntu 中加载 dots.tts 模型并通过 GPU 推理。

---

## 核心特性

- **Windows 原生桌面体验**：Tauri 打包的轻量级桌面窗口。
- **GPU 加速推理**：后端基于 PyTorch + CUDA，在 WSL2 中调用 NVIDIA 显卡。
- **单段克隆**：一次选择参考音频即可合成，无需训练说话人模型。
- **多格式支持**：参考音频支持常见有损/无损格式。
- **可调参数**：`num_steps`、`guidance_scale`、`language` 等高级参数可展开调整。
- **导出 WAV**：合成结果可直接播放或保存为 48kHz 16-bit PCM WAV。

---

## 架构

```
┌─────────────────────────────────────┐
│         Windows 桌面前端             │
│   Tauri 2.x + React + TypeScript    │
│            localhost:5173           │
└──────────────┬──────────────────────┘
               │ HTTP /api/health
               │ HTTP POST /api/clone
               ▼
┌─────────────────────────────────────┐
│   WSL2 Ubuntu-24.04                 │
│   Python FastAPI + dots.tts         │
│   localhost:8765                    │
└─────────────────────────────────────┘
```

- 前端通过 `fetch` 调用后端的 `/api/health` 与 `/api/clone`。
- 后端加载 `rednote-hilab/dots.tts-base` 模型，首次启动需下载约 5 GB 模型文件。
- 前端选择的 Windows 音频路径会自动转换为 WSL2 `/mnt/d/...` 路径传给后端。

---

## 快速开始

详细安装步骤请见 [docs/installation.md](docs/installation.md)。以下是最小启动流程：

### 1. 环境要求

- Windows 10/11 + WSL2 + Ubuntu-24.04
- NVIDIA 显卡 + 驱动 + WSL2 CUDA
- Git、Node.js 18+、Rust、Tauri CLI

### 2. 克隆代码

```powershell
git clone https://github.com/<your-username>/tts-work.git D:/code/tts-work
git -c http.proxy= -c https.proxy= clone https://github.com/rednote-hilab/dots.tts.git D:/code/dots.tts
```

### 3. 安装后端（WSL2）

```powershell
# 安装 miniconda
wsl -d Ubuntu-24.04 -- bash /mnt/d/code/tts-work/scripts/wsl_install_conda.sh

# 创建 dots_tts 环境并安装 dots.tts
wsl -d Ubuntu-24.04 -- bash /mnt/d/code/tts-work/scripts/wsl_install_dotstts.sh
```

### 4. 安装前端（Windows）

```powershell
cd D:/code/tts-work/frontend
npm install
```

### 5. 启动应用

终端 1 — 后端：

```powershell
wsl -d Ubuntu-24.04 -- bash /mnt/d/code/tts-work/scripts/wsl_run_backend.sh
```

终端 2 — 前端：

```powershell
cd D:/code/tts-work
tauri dev
```

后端就绪后，桌面窗口会显示“就绪”，即可开始合成。

---

## 使用说明

1. **等待就绪**：窗口顶部状态药丸变绿后，后端模型已加载完成。
2. **选择参考音频**：点击“选择文件”，支持 `wav/mp3/flac/ogg/m4a`。
3. **输入参考转录**：填写参考音频对应的文本内容。
4. **输入目标文本**：填写需要合成的中文文本。
5. **展开高级参数**（可选）：调整 `num_steps`、`guidance_scale`、`language`。
6. **点击合成**：首次合成可能需要 10-60 秒，后续复用 prompt 缓存会更快。
7. **播放 / 保存**：合成完成后可试听，或导出 WAV 文件。

---

## 项目结构

```
.
├── backend/             # Python FastAPI 后端
│   ├── app.py           #   FastAPI 入口：/api/health、/api/clone
│   ├── clone.py         #   合成逻辑：调用 dots.tts 并编码 WAV
│   ├── runtime.py       #   模型加载与 runtime 管理
│   ├── paths.py         #   Windows 路径转 WSL2 路径
│   └── tests/           #   后端单元测试
├── frontend/            # React + Vite + TypeScript 前端
│   ├── src/
│   │   ├── App.tsx      #   应用主框架与状态轮询
│   │   ├── api.ts       #   HTTP 客户端
│   │   ├── paths.ts     #   Windows → WSL2 路径转换
│   │   ├── pages/       #   页面组件
│   │   └── components/  #   可复用组件
│   └── package.json
├── src-tauri/           # Tauri 2.x Rust 桌面壳
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   └── src/
├── scripts/             # WSL2 辅助脚本
│   ├── wsl_install_conda.sh
│   ├── wsl_install_dotstts.sh
│   ├── wsl_run_backend.sh
│   ├── wsl_check_env.sh
│   └── wsl_check_cache.sh
├── docs/                # 文档
│   ├── installation.md  #   详细安装手册
│   └── wechat-qr.jpg
├── spec/                # 项目级 spec
├── openspec/            # OpenSpec 需求级变更管理
├── CLAUDE.md            # Claude Code 协作指引
├── LICENSE              # MIT
└── README.md            # 本文件
```

---

## 开发说明

### 分支模型

本项目采用 `version/v*` + `feature/*` 的两级分支模型：

```
main ── version/v0.1 ── feature/single-continuation-clone
```

详细工作流见 [CLAUDE.md](CLAUDE.md)。

### 后端端口

默认端口 `8765`，可通过环境变量修改：

```bash
export TTS_PORT=8766
```

修改后需同步设置 `frontend/.env`：

```env
VITE_API_BASE=http://127.0.0.1:8766
```

### 模型下载镜像

脚本 `wsl_run_backend.sh` 已默认设置：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

---

## 常见问题

**Q: 前端报 fetch failed / CORS 错误**
A: 确认后端已启动且 `curl http://127.0.0.1:8765/api/health` 返回 `ready`。后端已配置 `allow_origins=["*"]`，通常无需额外处理。

**Q: 合成时报 `NoBackendError`**
A: WSL2 缺少 ffmpeg，参考音频无法解码。执行：

```bash
wsl -d Ubuntu-24.04
sudo apt-get update
sudo apt-get install -y ffmpeg
```

**Q: 后端 health 不通**
A: 重启 WSL2 网络：`wsl --shutdown`，然后重新启动后端。

**Q: `tauri dev` 报 5173 端口占用**
A: 关闭所有 node 进程或重启电脑。详见 [docs/installation.md](docs/installation.md) 故障排查章节。

---

## 许可证

MIT
