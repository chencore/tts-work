# Tasks: single-continuation-clone

- [ ] 1. 后端 `paths.py`：Windows → WSL2 路径转换 + `validate_prompt_audio` 校验函数
- [ ] 2. 后端 `clone.py`：`synthesize_clone()` 合成 + soundfile 编码 wav bytes
- [ ] 3. 后端 `app.py`：注册 `POST /api/clone` 路由 + `CloneRequest` Pydantic schema
- [ ] 4. 后端单元验证：`python -c` 跑一遍合成（用一段短样例音频），确认 wav bytes 落盘能播
- [ ] 5. Tauri：`Cargo.toml` 加 `tauri-plugin-dialog` + `tauri-plugin-fs`，`cargo build` 过
- [ ] 6. Tauri：`capabilities/default.json` 授 `dialog:allow-open`、`dialog:allow-save`、`fs:allow-write-binary-file` + scope `**`
- [ ] 7. 前端 `paths.ts`：`winToWsl2()` 转换函数
- [ ] 8. 前端 `api.ts`：`cloneSynth()` + `CloneParams` 类型
- [ ] 9. 前端 `components/AdvancedParams.tsx`：折叠面板（num_steps / guidance_scale / language）
- [ ] 10. 前端 `pages/ClonePage.tsx`：完整 UI（选文件/转录/文本/高级/合成/试听/保存）
- [ ] 11. 前端 `App.tsx`：根据 `/api/health` status 切到 ClonePage（ready 时）
- [ ] 12. 安装 `@tauri-apps/plugin-dialog` + `@tauri-apps/plugin-fs` npm 包
- [ ] 13. 同步修订 `spec/requirements.md` 非目标条目（去 seed / guidance 1.0→1.2 / language=zh 默认）
- [ ] 14. 端到端验证：两终端起服务，UI 完整流程跑通（选文件→合成→试听→保存），4 类错误场景验证
