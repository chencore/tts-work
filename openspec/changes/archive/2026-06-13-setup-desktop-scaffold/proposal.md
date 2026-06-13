# Proposal: setup-desktop-scaffold

## 是什么（What）

搭建 Tauri + React + TS 桌面壳骨架，并集成 Python FastAPI 后端 + dots.tts 模型常驻加载。完成后整个 v0.1 应用的技术底盘就绪，但尚无任何 TTS 合成功能。

## 为什么（Why）

v0.1 的所有后续任务（克隆 UI、音色库、批量合成）都依赖：

- 一个能跑起来的桌面窗口
- 一个加载好 dots.tts 模型的 Python 后端
- 前后端能通信

本任务一次性把这些基础设施搭好，后续任务只做业务功能。

## 范围（Scope）

### 包含

- 项目目录结构（`src-tauri/`、`frontend/`、`backend/`）
- Tauri Rust 壳 + 配置（dev 模式即可）
- React + Vite + TS 前端骨架
- Python FastAPI 后端 + dots.tts 模型加载（singleton，启动时常驻 GPU）
- `GET /api/health` 端点
- 极简前端 UI：轮询 health，显示模型加载状态 + GPU 名
- dev 启动文档（README）

### 不包含（明确排除）

- 任何 TTS 合成端点 → `single-continuation-clone`
- 输入框、文件上传、试听 → `single-continuation-clone`
- 音色库 UI / 存储 → `voice-library`
- 批量合成 → `batch-synthesis`
- PyInstaller 打包成 sidecar / 安装包 → `package-release`
- Tauri 自动 spawn Python（dev 阶段两终端分别起）
- 自动化测试、CI

## 成功标准

- [ ] `python -m backend.app` 启动后，dots.tts 模型加载完毕，`/api/health` 返回 `status=ready`
- [ ] `cargo tauri dev` 起的桌面窗口显示 "等待 → 加载中 → 就绪 + GPU 名"
- [ ] 多次刷新窗口，模型不重载（runtime 单例）
- [ ] 后端崩溃 / 端口占用时前端显示明确错误（不是白屏）
