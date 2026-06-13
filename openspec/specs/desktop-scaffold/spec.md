# Spec: desktop-scaffold

> v0.1 桌面应用的基础架构骨架。本 spec 描述 setup-desktop-scaffold 变更引入后的长期规格。

## Scenario: 应用启动流程

- **WHEN** 用户运行 `cargo tauri dev` 或最终安装包
- **THEN** 桌面窗口打开，前端启动后向 `http://127.0.0.1:8765/api/health` 每秒轮询
- **AND** Python 后端进程在加载 dots.tts 模型（首次启动还需下载权重）
- **AND** 前端在模型加载完成前显示 "加载中"，加载完成后显示 "就绪 · GPU: <name>"

## Scenario: 模型常驻复用

- **WHEN** 前端多次刷新窗口或发起多次 health 请求
- **THEN** dots.tts 模型在 Python 进程内**只加载一次**
- **AND** 后续所有请求复用同一 `DotsTtsRuntime` 实例，不重载

## Scenario: 后端不可达

- **WHEN** Python 后端未启动 / 端口被占用 / 进程崩溃
- **THEN** 前端显示 "等待后端启动..." 或具体错误信息（不是白屏）
- **AND** 不影响 Tauri 窗口本身的可用性

## Scenario: dev 工作流

- **WHEN** 开发者按照 README 指引执行环境准备和两终端启动
- **THEN** 所有依赖（conda env `dots_tts`、torch+CUDA、frontend npm 包）按文档可一次装好
- **AND** 两终端分别启动 Python 后端（`python -m backend.app`）和 Tauri 桌面壳（`cargo tauri dev`）

## Scenario: 端口与端点约定

- **WHEN** 任何前端代码访问后端
- **THEN** 使用固定 `http://127.0.0.1:8765`（可由 `TTS_PORT` 环境变量覆盖）
- **AND** 健康检查端点为 `GET /api/health`，返回 `{status, model, gpu, elapsed_ms, error?}`
- **AND** `status ∈ {"loading", "ready", "error"}`
