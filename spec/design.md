# Design

> **维护规则**：本文件是**项目整体设计与架构决策**，仅在**人工明确要求**时修改。AI 不得擅自更新。

---

## 1. 技术栈

| 层 | 选型 | 理由 |
|----|------|------|
| 后端 | Python 3.10 + FastAPI（本地 HTTP on `127.0.0.1:8765`） | dots.tts 官方提供 Python API（`DotsTtsRuntime`），原生集成最直接；FastAPI `/docs` 免费、可 curl 调试 |
| 桌面壳 | Tauri 2.x（Rust） | 体积小、性能好；Electron 150MB+ 太重，PyWebView 生态小 |
| 前端 UI | React + Vite + TypeScript | Tauri 官方默认模板、生态最大 |
| **Python 运行环境** | **WSL2 Ubuntu-24.04 + conda env `dots_tts`** | dots.tts 经 WeTextProcessing 依赖 pynini，PyPI 无 Windows wheel；详见 §6 决策 4 |
| 数据库 | 无（音色库用本地文件） | 个人自用，无并发，无需 DB |
| 部署 | 纯本地桌面 App（dev 阶段双终端：WSL2 后端 + Windows Tauri） | 个人自用，无服务端，零网络 |

## 2. 系统架构

```
[ 桌面 UI ] ⇄ [ Python 后端（本地 HTTP/IPC）] ⇄ [ dots.tts Runtime（GPU 常驻）]
                    ↓
             [ 音色库（本地文件）]
```

应用启动时加载 dots.tts 模型并常驻 GPU，所有合成请求复用同一 runtime。桌面壳与 Python 后端通过本地 HTTP 或 IPC 通信（具体方式取决于桌面壳选型）。

## 3. 模块划分

- **ui** — 桌面 App 界面（克隆表单、音色库管理、批量合成）
- **voice-library** — 音色条目的本地存储与 CRUD
- **synthesis** — 调用 dots.tts 进行 continuation 克隆（单段 + 批量）
- **model-runtime** — dots.tts 模型加载 / 常驻 / 复用

## 4. 数据模型（核心实体）

### Voice（音色条目）

- `id`, `name`, `note`, `audio_path`, `transcript`, `created_at`

### BatchJob（批量任务，运行时态）

- `voice_id`, `lines[]`, `output_dir`, `progress`, `errors[]`

## 5. 关键接口约定

- **桌面壳 ⇄ Python 后端**：本地 HTTP（FastAPI）或 IPC，取决于桌面壳选型
- **模型生命周期**：应用启动加载、常驻；合成请求复用同一 runtime，不重载
- **错误处理**：单段失败返回错误信息，不中断批量合成

## 6. 关键决策与权衡

### 决策 1：纯本地推理，不做远程服务

- **选择**：桌面 App 内嵌 Python，直接调 dots.tts
- **放弃的方案**：云 GPU API / C/S 架构
- **理由**：个人自用 + 本地有 ≥12GB GPU，纯本地最简、零网络延迟、零使用成本

### 决策 2：只做 continuation 克隆

- **选择**：仅 continuation（参考音频 + 转录）
- **放弃的方案**：x-vector-only / random-voice
- **理由**：continuation 是官方推荐、效果最好；x-vector-only 效果较差；random-voice 无 fine-tuning 时无意义

### 决策 3：参考转录手输，不集成 ASR

- **选择**：用户手输转录
- **放弃的方案**：集成 Whisper 自动 ASR
- **理由**：v0.1 聚焦最简；ASR 增加约 1GB 依赖；个人自用克隆自己/家人音色，转录已知

### 决策 4：Python 后端跑在 WSL2，而非原生 Windows

- **选择**：WSL2 Ubuntu-24.04 + conda env `dots_tts`（Python 3.10）
- **放弃的方案**：原生 Windows conda / Docker
- **理由**：dots.tts 通过 `WeTextProcessing → pynini` 依赖 OpenFst 的 Python 绑定，pynini 在 PyPI 只有源码包且用 GCC/Clang flag（`-Wno-register`），MSVC 不识别，**原生 Windows 装不上**；WSL2 与官方 Linux 平台一致，最少踩坑
- **影响**：
  - Python 后端进程跑在 WSL2，Tauri 壳跑在 Windows 主机
  - 两者通过 `127.0.0.1:8765` 通信（WSL2 默认 localhost 双向转发到 Windows 主机）
  - 项目代码继续放 Windows 文件系统（`D:\code\tts-work`），WSL2 通过 `/mnt/d/code/tts-work` 访问
  - 模型权重缓存走 WSL2 用户 home（`~/.cache/huggingface`），Linux 文件系统下 IO 快
  - **打包发行方式**留待 `package-release` 任务设计（v0.1 当前只考虑 dev 流）

## 7. 待定项（Open Questions）

- ~~**桌面壳技术栈**（Electron / Tauri / PyWebView）~~ ✓ **已定**：Tauri 2.x（见 §1）
- **音色库存储格式**（JSON 索引 + 音频文件 / SQLite）—— voice-library 启动前定
- **目标 OS**（Windows only / 跨平台）—— package-release 启动前定
- **默认参数具体值**（num_steps / guidance_scale / language / seed）—— single-continuation-clone 启动前定
- ~~**桌面壳 ⇄ Python 后端通信方式**（HTTP / IPC）~~ ✓ **已定**：本地 HTTP（FastAPI on `127.0.0.1:8765`，端口可由 `TTS_PORT` 覆盖）
- **打包发行方式**（WSL2 + conda 自动装 / Docker 镜像 / 其他）—— package-release 启动前定
