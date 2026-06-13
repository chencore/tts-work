# Development Log

> **维护规则**：每次 PR 合并后，由 AI 自动追加一条记录。
>
> 每条记录应包含：日期、变更名、摘要、关键决策/坑点。

---

## Entry Template

```markdown
### YYYY-MM-DD · <change-name>

**摘要**：一句话说清楚这次变更做了什么。

**关键决策**：
- 决策点 1 — 选了什么、放弃了什么、为什么
- 决策点 2 — ...

**踩坑 / 经验**：
- 坑点描述 + 如何解决（可选）

**相关产出**：
- 归档位置：`openspec/changes/archive/<change-name>/`
- PR：#xxx（如适用）
```

---

## Log Entries

<!-- 最新条目在最上面 -->

### 2026-06-13 · v0.1-kickoff

**摘要**：v0.1 版本 kickoff——确立个人自用本地语音克隆桌面应用范围，写入项目级 spec。

**关键决策**：

- 定位为个人自用桌面 App（非 C 端 / 非 API 平台），纯本地 NVIDIA GPU（≥12GB）推理
- 形态选桌面 App（Electron / Tauri / PyWebView 待 design 阶段定）
- 核心功能收敛为 continuation 克隆 + 音色库 + 批量合成三项
- 参考转录手输，不集成 ASR；v0.1 仅中文
- 明确不做：参数面板、历史记录、x-vector/random 克隆、fine-tuning、流式、多语言、AI 水印

**相关产出**：

- 创建版本分支 `version/v0.1`（从 main 拉出，未推送远程）
- `spec/requirements.md`：新增 R-v0.1-ck-1/2/3 + 非功能 / 非目标 / 成功标准 + 修订历史
- `spec/tasks.md`：新增 `## 版本 v0.1` 块，5 个 task（setup-desktop-scaffold / single-continuation-clone / voice-library / batch-synthesis / package-release）
- `spec/design.md`：高层架构（纯本地推理 / continuation only / 手输转录）+ 5 项待定

### 2026-04-16 · bootstrap-speccoding-template

**摘要**：从 SpecCoding Template 初始化项目骨架。

**关键决策**：
- 采用「两级 Spec 体系」：`spec/` 管全局、`openspec/` 管单次变更
- 开发工作流固化为七阶段：git branch → scaffold → brainstorm → plan → execute → archive → merge

**相关产出**：
- 项目级 spec 文档骨架（requirements / design / tasks / devlog / structure）
- OpenSpec 配置 + 示例归档变更 `example-add-user-auth`
