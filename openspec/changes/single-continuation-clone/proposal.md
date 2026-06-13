# Proposal: single-continuation-clone

## 是什么

v0.1 R-v0.1-ck-1：单段 continuation 克隆功能。用户在桌面 App 里输入目标文本 + 选参考音频 + 手输参考转录，调 dots.tts continuation 模式合成中文语音，前端试听 + Tauri 写盘保存到任意位置。

## 为什么

这是 v0.1 三项核心功能里最基础的一项——voice-library 和 batch-synthesis 都建立在"能合成单段"之上。先把单段跑通 + 接口稳定，后续两个 task 才能直接复用。

## 范围

- 单段中文文本（不超过 dots.tts `max_generate_length` ≈ 几十秒音频）→ 单段 48kHz wav
- continuation 克隆：参考音频 + 参考转录 + 目标文本
- 试听（HTML `<audio>`）
- 保存到用户指定路径（Tauri `dialog.save()` + `fs.writeBinaryFile()`）
- UI"高级"折叠面板可调 `num_steps` / `guidance_scale` / `language(zh|none)`

## 不做（明确非目标）

- 音色库管理（下一个 task：voice-library）
- 批量合成（下下个 task：batch-synthesis）
- 流式合成（v0.1 同步阻塞即可）
- 自动 ASR 转录（v0.1 明确非目标，转录手输）
- 历史记录 / 重命名 / 多次保存管理
- seed 控制（dots.tts API 不支持，去掉该概念）
- 参数面板（除"高级"折叠里的三项，其他参数不暴露）

## 同步修订 spec

本变更同时修订 `spec/requirements.md` 非目标条目，去掉 `seed=42`、把 `guidance=1.0` 改成 `guidance_scale=1.2`（与 dots.tts 实际默认对齐）、`language=ZH/none` 改为"默认 zh，高级面板可切 none"。
