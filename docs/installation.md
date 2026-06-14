# tts-work 安装手册

> 本手册面向最终用户与开发者，说明如何在 Windows + WSL2 环境下安装、运行并打包 tts-work 语音克隆桌面应用。

---

## 1. 架构与前提

### 1.1 运行架构

- **前端（Windows）**：Tauri 2.x + React，打包为 Windows 桌面程序。
- **后端（WSL2 Ubuntu-24.04）**：Python + FastAPI + dots.tts 模型。
- **通信方式**：前端通过 `http://127.0.0.1:8765` 访问后端；WSL2 自动把 Windows 的 localhost 转发到 WSL2 内部。

### 1.2 为什么需要 WSL2

dots.tts 依赖 `pynini`、`WeTextProcessing` 等库，PyPI 没有 Windows 预编译 wheel，因此后端必须在 WSL2 Linux 环境中运行。

### 1.3 系统要求

| 组件 | 最低要求 | 推荐 |
|------|---------|------|
| 操作系统 | Windows 10/11 64 位 | Windows 11 + WSL2 |
| WSL 发行版 | Ubuntu-24.04 | Ubuntu-24.04 |
| 显卡 | NVIDIA GTX 10 系列 + 8 GB 显存 | NVIDIA RTX 3060 12 GB 或更高 |
| 显存 | 8 GB | 12 GB |
| 内存 | 16 GB | 32 GB |
| 硬盘空间 | 30 GB 可用 | 50 GB 可用（含模型、conda、缓存） |
| 网络 | 可访问 GitHub / HuggingFace | 可访问 hf-mirror.com 镜像 |

必须安装的 Windows 软件：

- [Git](https://git-scm.com/download/win)
- [Node.js 18+](https://nodejs.org/)
- [Rust](https://rustup.rs/)（Tauri 需要）
- [Tauri CLI](https://tauri.app/start/prerequisites/)

---

## 2. 一次性环境准备

### 2.1 启用 WSL2 并安装 Ubuntu-24.04

在 PowerShell（管理员）中执行：

```powershell
wsl --install -d Ubuntu-24.04
```

安装完成后重启电脑，按提示创建 Ubuntu 用户名和密码。

验证：

```powershell
wsl --status
wsl --list --verbose
```

应看到 `Ubuntu-24.04` 且 `VERSION` 为 `2`。

### 2.2 更新 Ubuntu 基础包

打开 WSL2 终端：

```bash
wsl -d Ubuntu-24.04
```

在 WSL2 内执行：

```bash
sudo apt-get update
sudo apt-get install -y build-essential python3-dev python3-pip python3-venv wget git ffmpeg
```

`ffmpeg` 用于解码 `mp3/m4a/ogg` 等参考音频格式，**必须安装**。

### 2.3 安装 Windows 开发工具

#### 2.3.1 Git

```powershell
git --version
```

未安装请从 [git-scm.com](https://git-scm.com/download/win) 下载。

#### 2.3.2 Node.js

```powershell
node --version
npm --version
```

要求 Node.js ≥ 18。建议使用 [nvm-windows](https://github.com/coreybutler/nvm-windows) 管理版本：

```powershell
nvm install 24.15.0
nvm use 24.15.0
```

#### 2.3.3 Rust

在 PowerShell 中执行：

```powershell
winget install Rustlang.Rustup
```

或访问 https://rustup.rs/ 下载安装。安装后重启终端：

```powershell
cargo --version
rustc --version
```

#### 2.3.4 Tauri CLI

```powershell
cargo install tauri-cli
```

或：

```powershell
npm install -g @tauri-apps/cli
```

---

## 3. 获取项目代码

### 3.1 克隆主项目

```powershell
git clone https://github.com/<your-username>/tts-work.git D:/code/tts-work
cd D:/code/tts-work
```

如果后续要修改代码，建议 fork 到自己的仓库再 clone。

### 3.2 克隆 dots.tts 源码（本地安装用）

```powershell
git -c http.proxy= -c https.proxy= clone https://github.com/rednote-hilab/dots.tts.git D:/code/dots.tts
```

> 如果 Git 代理报错，加上 `-c http.proxy= -c https.proxy=` 临时禁用代理。

---

## 4. 安装后端环境（WSL2）

项目已提供自动化脚本，在 Windows PowerShell 中执行即可。

### 4.1 安装 miniconda

```powershell
wsl -d Ubuntu-24.04 -- bash /mnt/d/code/tts-work/scripts/wsl_install_conda.sh
```

脚本会从清华大学镜像下载 miniconda 并安装到 `~/miniconda3`。安装完成后**关闭并重新打开 WSL2 终端**，让 conda 初始化生效。

### 4.2 创建 dots_tts 环境并安装依赖

```powershell
wsl -d Ubuntu-24.04 -- bash /mnt/d/code/tts-work/scripts/wsl_install_dotstts.sh
```

脚本会：

1. 创建 `dots_tts` conda 环境（Python 3.10）。
2. 配置 pip 使用清华 PyPI 镜像。
3. 安装 FastAPI + Uvicorn。
4. 从本地 `/mnt/d/code/dots.tts` 以 editable 模式安装 `dots.tts`，并应用官方推荐约束文件（含 PyTorch + CUDA 版本）。
5. 验证 PyTorch 能否识别 GPU。

首次执行需要下载 PyTorch CUDA wheel 和 dots.tts 依赖，约 5-10 GB，耗时 10-30 分钟，取决于网速。

### 4.3 验证后端环境

```powershell
wsl -d Ubuntu-24.04 -- bash /mnt/d/code/tts-work/scripts/wsl_check_env.sh
```

正常应输出各库版本号，无报错。

检查 GPU：

```powershell
wsl -d Ubuntu-24.04 -- bash -c "source ~/miniconda3/etc/profile.d/conda.sh && conda activate dots_tts && python -c 'import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))'"
```

期望输出类似：

```
true NVIDIA GeForce RTX 3060
```

### 4.4 安装 ffmpeg（如未安装）

如果后续合成时提示 `NoBackendError`，说明 WSL2 缺少 ffmpeg：

```bash
wsl -d Ubuntu-24.04
sudo apt-get update
sudo apt-get install -y ffmpeg
which ffmpeg
```

---

## 5. 安装前端环境（Windows）

### 5.1 安装前端依赖

```powershell
cd D:/code/tts-work/frontend
npm install
```

### 5.2 配置 cargo（首次 tauri dev 可能遇到代理问题）

如果 `tauri dev` 报 `Failed to connect to 127.0.0.1 port xxxxx`，是 Windows 系统代理残留导致 libgit2 读取了失效代理。创建 `~/.cargo/config.toml`：

```toml
[http]
proxy = ""

[net]
git-fetch-with-cli = true
```

### 5.3 更新 Rust 工具链（如编译报错）

```powershell
rustup update stable
```

---

## 6. 首次启动应用

需要同时运行两个进程：后端（WSL2）和前端（Windows）。

### 6.1 启动后端

PowerShell：

```powershell
wsl -d Ubuntu-24.04 -- bash /mnt/d/code/tts-work/scripts/wsl_run_backend.sh
```

或手动进入 WSL2：

```bash
wsl -d Ubuntu-24.04
conda activate dots_tts
cd /mnt/d/code/tts-work
export HF_ENDPOINT=https://hf-mirror.com
python -m backend.app
```

首次启动会自动从 HuggingFace 下载 `rednote-hilab/dots.tts-base` 模型，约 5 GB，耗时取决于网速。下载完成后模型会缓存到 `~/.cache/huggingface/`。

验证后端就绪：

```powershell
curl http://127.0.0.1:8765/api/health
```

期望返回：

```json
{"status":"ready","model":"rednote-hilab/dots.tts-base","gpu":"NVIDIA GeForce RTX 3060","elapsed_ms":...,"error":null}
```

### 6.2 启动前端

在另一个 PowerShell 窗口：

```powershell
cd D:/code/tts-work
tauri dev
```

`tauri dev` 会：

1. 自动启动 Vite 开发服务器（默认 `http://localhost:5173`，若被占用则顺延到 5174、5175…）。
2. 编译 Rust 原生代码。
3. 弹出桌面窗口。

---

## 7. 使用应用

1. **等待就绪**：窗口顶部状态药丸显示为绿色“就绪”后，方可合成。
2. **选择参考音频**：点击“选择文件”，支持 `wav/mp3/flac/ogg/m4a`。
3. **输入参考转录**：填写参考音频对应的文本。
4. **输入目标文本**：填写想要合成的中文文本。目标文本超过约 60 字时，后端会自动按标点分段合成并拼接音频。
5. **调整高级参数**（可选）：展开“高级参数”可修改 `num_steps`、`guidance_scale`、`language`。
6. **点击合成**：首次合成需要加载 prompt，可能耗时 10-60 秒；长文本会分成多段依次生成，总时间随字数增加。
7. **播放 / 保存**：合成完成后可在线试听，或点击“保存到…”导出 WAV 文件。

---

## 8. 打包为可执行文件 / 安装包

### 8.1 构建前端

```powershell
cd D:/code/tts-work/frontend
npm run build
```

产物在 `frontend/dist/`。

### 8.2 打包 Tauri 应用

```powershell
cd D:/code/tts-work
tauri build
```

首次打包需要编译 release 版本的 Rust 代码，耗时数分钟。产物位于：

- `src-tauri/target/release/tts-work.exe`（可直接运行的单文件）
- `src-tauri/target/release/bundle/`（安装包 `.msi`、`.exe` 等）

### 8.3 分发说明

打包后的桌面程序**只包含前端**。用户机器上仍需：

1. 安装 WSL2 + Ubuntu-24.04。
2. 按本手册第 4 节配置好 `dots_tts` conda 环境。
3. 启动后端（可以双击一个 `.bat` 脚本，见下）。

建议随安装包附带一个启动脚本 `start-backend.bat`：

```bat
@echo off
wsl -d Ubuntu-24.04 -- bash /mnt/d/code/tts-work/scripts/wsl_run_backend.sh
```

---

## 9. 常见问题排查

### 9.1 后端 health 不通 / 前端 fetch failed

1. 确认后端进程已启动且模型加载完成（`status=ready`）。
2. 在 Windows 上测试：
   ```powershell
   curl http://127.0.0.1:8765/api/health
   ```
3. 若不通，重启 WSL2 网络：
   ```powershell
   wsl --shutdown
   ```
   然后重新启动后端。

### 9.2 端口 8765 被占用

```powershell
netstat -ano | findstr :8765
```

结束占用进程，或改用其他端口：

```bash
export TTS_PORT=8766
```

修改后需在 `frontend/.env` 中设置：

```env
VITE_API_BASE=http://127.0.0.1:8766
```

然后重新构建前端。

### 9.3 合成时报 `NoBackendError`

WSL2 缺少 ffmpeg，参考音频无法解码。安装：

```bash
wsl -d Ubuntu-24.04
sudo apt-get update
sudo apt-get install -y ffmpeg
```

### 9.4 模型下载慢 / 失败

在 WSL2 中设置 HuggingFace 镜像：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

脚本 `wsl_run_backend.sh` 已默认设置此镜像。

### 9.5 `tauri dev` 报 5173 端口占用

关闭残留 node 进程或重启电脑。Vite 会自动尝试 5174、5175 等端口。

### 9.6 Rust 编译报错 `rustc 1.87.0 is not supported`

```powershell
rustup update stable
```

### 9.7 npm 报错 `Class extends value undefined`

通常是 nvm 多版本 PATH 污染。临时指定 Node 路径：

```powershell
$env:PATH = "C:\Program Files (x86)\nvm\v24.15.0;$env:PATH"
```

### 9.9 合成时报 `CUDA error: out of memory`

显存不足。消费级显卡（如 RTX 3060 12GB）在目标文本较长或参考音频较长时可能触发。

本项目已在后端实现自动文本分段：当目标文本超过约 60 个字符时，会按标点拆成多段分别合成，再把音频拼接返回。这能显著降低峰值显存。

如果仍然 OOM，可继续尝试：

1. **缩短目标文本**：一次合成的文本越短，占用的显存越少。
2. **缩短参考音频**：参考音频过长会增加 prompt 缓存占用。
3. **降低 `num_steps`**：在高级参数中将 `num_steps` 从 10 降到 5~8。
4. **降低最大生成长度**：在启动后端前设置环境变量：
   ```bash
   export DOTS_TTS_MAX_LENGTH=300
   python -m backend.app
   ```
   默认值已改为 400（dots.tts 原默认 500）。数值越小越省显存，但可合成的最大音频长度也越短。
5. **重启后端**：每次修改 `DOTS_TTS_MAX_LENGTH` 后必须重启后端才能生效。

### 9.10 GPU 不可用

1. 确认已安装 NVIDIA Windows 显卡驱动。
2. 确认 WSL2 已安装 CUDA Toolkit：
   ```bash
   nvidia-smi
   ```
3. 如果 `torch.cuda.is_available()` 为 false，可能是 PyTorch 装成了 CPU 版本，重新执行 `wsl_install_dotstts.sh`。

---

## 10. 目录速查

| 路径 | 说明 |
|------|------|
| `D:/code/tts-work` | 主项目 |
| `D:/code/dots.tts` | dots.tts 源码（本地 editable 安装） |
| `/mnt/d/code/tts-work` | WSL2 中对应的主项目路径 |
| `~/miniconda3/envs/dots_tts` | conda 环境 |
| `~/.cache/huggingface/` | 模型缓存 |
| `frontend/dist/` | 前端构建产物 |
| `src-tauri/target/release/bundle/` | 桌面安装包 |

---

## 11. 日常更新

### 11.1 更新项目代码

```powershell
cd D:/code/tts-work
git pull
```

### 11.2 更新 dots.tts

```powershell
cd D:/code/dots.tts
git pull
```

然后在 WSL2 中重新安装：

```bash
wsl -d Ubuntu-24.04
source ~/miniconda3/etc/profile.d/conda.sh
conda activate dots_tts
pip install --progress-bar off -e /mnt/d/code/dots.tts -c /mnt/d/code/dots.tts/constraints/recommended.txt --force-reinstall --no-deps
```

### 11.3 清理模型缓存

```bash
wsl -d Ubuntu-24.04
rm -rf ~/.cache/huggingface/hub/models--rednote-hilab--dots.tts-base
```

---

**至此，tts-work 已安装并可以运行。** 如仍有问题，请检查后端日志与浏览器/Tauri 开发者工具（F12）中的网络请求详情。
