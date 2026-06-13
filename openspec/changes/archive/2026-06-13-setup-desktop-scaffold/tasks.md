# Tasks: setup-desktop-scaffold

- [x] 1. 创建项目目录结构（`src-tauri/`、`frontend/`、`backend/`）
- [x] 2. 初始化 Tauri 2.x 项目（`cargo tauri init`），配置 `tauri.conf.json`（devUrl、frontendDist、allowlist）
- [x] 3. 初始化 React + Vite + TS（`frontend/` 下 `npm create vite@latest . -- --template react-ts`）
- [x] 4. 编写 `backend/requirements.txt`（dots.tts from git + fastapi + uvicorn + 显式 torch 版本）
- [x] 5. 实现 `backend/runtime.py`（dots.tts 模型单例：同步加载、状态机、`get_runtime()`）
- [x] 6. 实现 `backend/app.py`（FastAPI 实例 + `/api/health` + CORS + 端口环境变量）
- [x] 7. 实现 `frontend/src/api.ts`（HTTP 客户端 + 错误类型）
- [x] 8. 实现 `frontend/src/App.tsx`（轮询 health + 四态视图）
- [x] 9. 更新 `README.md`（环境准备 + 两终端启动文档 + 故障排查）
- [x] 10. 端到端验证：两终端启动，桌面窗口显示 "等待 → 加载中 → 就绪 + GPU 名"
