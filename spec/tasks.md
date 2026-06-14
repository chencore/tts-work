# Tasks

> **维护规则**：
> - **任务内容**由人工维护，仅在人工明确要求时修改
> - **任务完成状态**由 AI 在对应 openspec 变更归档后自动勾选
>
> 每个任务对应 `openspec/changes/<task-name>/` 下的一个变更提案。

---

## 命名约定

- 任务名使用 **kebab-case**：`setup-desktop-scaffold`、`voice-library`
- 粒度：**一个提案能做完的事情**（通常 1~3 天工作量）
- 尽量独立：减少任务间依赖，便于并行推进

---

## 版本 v0.1

> 范围：个人自用本地语音克隆桌面应用（continuation 克隆 + 音色库 + 批量合成）

- [x] **setup-desktop-scaffold** — 搭建桌面 App 骨架 + Python 后端集成 dots.tts（技术选型 / 项目结构 / 模型加载常驻）✅ 2026-06-13
- [x] **single-continuation-clone** — 单段 continuation 克隆：UI（文本/参考音频/转录输入）+ 后端联动 + 试听 / 保存 wav ✅ 2026-06-14
- [ ] **voice-library** — 音色库：本地存储 + CRUD + 选择器接入克隆/批量
- [ ] **batch-synthesis** — 批量合成：多行文本解析 + 顺序生成 + 多 wav 输出 + 进度
- [ ] **package-release** — 桌面 App 打包发行（可安装包）

---

## 进度概览

- 总任务数：5
- 已完成：1（setup-desktop-scaffold）
- 进行中：0

（建议每完成一个版本手动更新以上数字）
