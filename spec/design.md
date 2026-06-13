# Design

> **维护规则**：本文件是**项目整体设计与架构决策**，仅在**人工明确要求**时修改。AI 不得擅自更新。

---

## 1. 技术栈

| 层 | 选型 | 理由 |
|----|------|------|
| 后端 | Python（直调 `dots_tts` 包） | dots.tts 官方提供 Python API（`DotsTtsRuntime`），原生集成最直接 |
| 桌面壳 | 待定（Electron / Tauri / PyWebView） | design 阶段决策，见待定项 |
| 前端 UI | 待定（取决于桌面壳选型） | |
| 数据库 | 无（音色库用本地文件） | 个人自用，无并发，无需 DB |
| 部署 | 纯本地桌面 App | 个人自用，无服务端，零网络 |

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

## 7. 待定项（Open Questions）

- **桌面壳技术栈**（Electron / Tauri / PyWebView）—— setup-desktop-scaffold 启动前定
- **音色库存储格式**（JSON 索引 + 音频文件 / SQLite）—— voice-library 启动前定
- **目标 OS**（Windows only / 跨平台）—— package-release 启动前定
- **默认参数具体值**（num_steps / guidance_scale / language / seed）—— single-continuation-clone 启动前定
- **桌面壳 ⇄ Python 后端通信方式**（HTTP / IPC）—— 随桌面壳技术栈一起定
