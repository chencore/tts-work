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

### 2026-06-14 · single-continuation-clone

**摘要**：实现单段 continuation 克隆端到端——桌面 UI（目标文本 / 参考音频 / 参考转录 / 高级参数）+ FastAPI `/api/clone` + dots.tts 推理 + WAV 试听与保存。

**关键决策**：

- 后端一次性加载模型，启动时同步阻塞，前端通过 `/api/health` 轮询状态
- 音频路径在 Windows 前端侧转换为 WSL2 `/mnt/d/...` 格式再传给后端
- 后端使用 `soundfile` 将 dots.tts 返回的 `torch.Tensor` 编码为 48kHz 16-bit PCM WAV bytes
- 前端文件保存走 Tauri `plugin-fs` 的 `writeFile`（v2 不再提供 `writeBinaryFile`）
- 开发模式下保留直接跨域调用 `http://127.0.0.1:8765`，后端 CORS 已配置 `allow_origins=["*"]`

**踩坑 / 经验**：

- dots.tts 返回的音频 tensor 形状可能是 `(1, 1, N)`，需要循环 squeeze -leading-1 维度后再交给 soundfile
- WSL2 缺少 ffmpeg 时 librosa 解码 mp3/m4a 会报 `NoBackendError`，已在错误提示中引导用户安装 ffmpeg
- Tauri dev 时旧 Vite/WebView2 进程残留会导致前端 502，需彻底清理 node.exe 与 msedgewebview2 进程
- 首次合成耗时较长（RTF 约 36），需在前端给出“合成中（可能需 10~30 秒）”提示

**相关产出**：

- 变更目录：`openspec/changes/single-continuation-clone/`
- 安装手册：[docs/installation.md](../docs/installation.md)
- 父分支：`version/v0.1`
- 备注：本次合并跳过了 `/opsx:archive` 归档步骤

### 2026-06-13 · setup-desktop-scaffold

**摘要**：搭建桌面 App 骨架——Tauri 2.x + React+Vite+TS 前端 + FastAPI 后端 + dots.tts 模型集成，dev 流程端到端跑通（WSL2 后端 + Windows Tauri 双终端，模型加载完毕后桌面窗口显示 "就绪 · GPU: RTX 3060"）。

**关键决策**：

- 桌面壳选 **Tauri 2.x**（放弃 Electron 体积太大、PyWebView 生态小）
- 前后端通信走 **本地 HTTP `127.0.0.1:8765`**（放弃 stdio JSON-RPC / Tauri events）——可 curl 调试、FastAPI `/docs` 免费、与 Tauri 解耦
- **Python 后端跑在 WSL2 Ubuntu-24.04**（放弃原生 Windows / Docker）——dots.tts 经 `WeTextProcessing → pynini` 依赖 OpenFst Python 绑定，PyPI 无 Windows wheel（MSVC 不识别 GCC flag `-Wno-register`），WSL2 与官方 Linux 平台一致最少踩坑
- 模型加载用**同步**而非懒加载——FastAPI 启动即触发，前端 health 能反映真实进度
- 项目代码放 Windows 文件系统（`D:\code\tts-work`），WSL2 通过 `/mnt/d/code/tts-work` 访问；模型权重走 WSL2 home（`~/.cache/huggingface`）

**踩坑 / 经验**：

- Windows IE 代理残留（`ProxyServer=127.0.0.1:50830` 即便 `ProxyEnable=0`）会被 libgit2 / cargo 读取——写 `~/.cargo/config.toml` 强制空代理 + `git-fetch-with-cli = true` 绕过
- Tauri 2.x 部分依赖（darling / plist / serde_with / time）要求 rustc 1.88+——`rustup update stable` 升到 1.96.0 解决
- nvm 多版本切换留 PATH 污染——`npx` 报 `Class extends value undefined`，临时用 v24 直接路径绕过
- HF 官方源下载慢——`HF_ENDPOINT=https://hf-mirror.com` 镜像加速（vocab.json 等小文件仍有 ReadTimeout，huggingface_hub 自动 retry 兜底）
- 模型权重 ~5GB 首次下载约 13 分钟（hf-mirror）

**相关产出**：

- 归档位置：`openspec/changes/archive/2026-06-13-setup-desktop-scaffold/`
- 长期 spec 同步：`openspec/specs/desktop-scaffold/spec.md`（端口/端点/状态机权威定义）
- 项目级 spec 同步：`spec/design.md` §1 技术栈表更新、§6 新增"决策 4：WSL2 而非原生 Windows"、§7 待定项勾掉桌面壳/通信方式两项
- 父分支：`version/v0.1`
- 后续待办：打包发行方式（WSL2 + conda 自动装 / Docker）留待 `package-release` 任务设计

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
