# Spec: synthesis

> 单段 continuation 克隆的长期规格。本 spec 描述 single-continuation-clone 变更引入后的稳定接口与行为。

## Scenario: 完整单段克隆流程

- **WHEN** 用户在桌面 App 输入目标文本 + 选参考音频 + 输入参考转录 + 点"合成"
- **THEN** 前端 POST `/api/clone`，body 为 JSON：`{text, prompt_audio_path, prompt_text, num_steps?, guidance_scale?, language?}`
- **AND** `prompt_audio_path` 必须是 WSL2 路径（`/mnt/<drive>/...`），由前端从 Windows 路径转换得来
- **AND** 后端校验 → 调 `dots.tts.runtime.generate()` → 把 audio Tensor 用 soundfile 编码为 16-bit PCM wav
- **AND** HTTP 响应 `Content-Type: audio/wav`，响应体即 wav bytes
- **AND** 前端用 `URL.createObjectURL(blob)` 喂给 `<audio controls>`，用户可点播放

## Scenario: 高级参数覆盖默认值

- **WHEN** 用户展开"高级参数"面板，调 `num_steps` / `guidance_scale` / `language(zh|none)`
- **THEN** 这些值随 POST body 一起传给后端，覆盖默认值（`num_steps=10, guidance_scale=1.2, language="zh"`）
- **AND** 不展开/不调时，后端用默认值
- **AND** `language="none"` 等价于 dots.tts `language=None`（不附语言标签）

## Scenario: 保存到指定位置

- **WHEN** 用户在试听后点"保存到..."
- **THEN** Tauri `dialog.save({ defaultPath: "clone.wav" })` 弹出，用户选目标 Windows 路径
- **AND** Tauri `fs.writeBinaryFile(targetPath, wavBytes)` 直接写盘（不经后端）
- **AND** UI 显示"已保存到 <路径>"

## Scenario: 参考音频路径无效

- **WHEN** 用户选的文件路径不是本地盘（如 UNC `\\server\share`、网络盘）
- **THEN** 前端 `winToWsl2()` 抛错，UI 在合成前显示"不支持的路径格式（仅本地盘 X:\\...）"
- **AND** 不发起 POST

## Scenario: 参考音频文件不存在或不可读

- **WHEN** 用户选的文件路径有效但 WSL2 侧读不到（权限/文件被删/路径大小写不匹配）
- **THEN** 后端返 HTTP 400，body 为 `{detail: "参考音频无效：..."}`
- **AND** UI 显示该 detail

## Scenario: 文本为空或转录为空

- **WHEN** 用户点"合成"但目标文本或参考转录为空
- **THEN** 前端挡一道（按钮 disabled 或 inline 提示）
- **AND** 即便绕过前端，后端返 HTTP 422 `{detail: "目标文本不能为空" / "参考转录不能为空"}`

## Scenario: 文本过长触发 max_generate_length

- **WHEN** 目标文本对应音频超过 dots.tts `max_generate_length`（约几十秒）
- **THEN** 后端抓 ValueError 返 HTTP 413 `{detail: "文本过长或不被模型接受：..."}`
- **AND** UI 显示该 detail，提示用户考虑拆分（批量合成在后续 task）

## Scenario: dots.tts 合成失败

- **WHEN** runtime.generate 抛非 ValueError 异常（GPU OOM / 模型内部错误）
- **THEN** 后端返 HTTP 500 `{detail: "合成失败：<类型>: <消息>"}`
- **AND** UI 显示该 detail，保留之前的合成结果（如果有）

## Scenario: 后端未就绪时合成

- **WHEN** `/api/health` 返回 `status != "ready"`
- **THEN** 前端 ClonePage "合成"按钮 disabled，按钮旁提示"等待模型加载"
- **AND** 即使强制发请求，后端 `get_runtime()` 抛 RuntimeError，HTTP 500 返回

## Scenario: 网络错误 / 后端不可达

- **WHEN** 前端 `fetch` 抛 TypeError（WSL2 没起、端口占用等）
- **THEN** 前端 `cloneSynth` 抛 `ApiError(kind="network")`
- **AND** UI 显示"网络错误：<消息>，请检查后端是否启动"，附重试按钮

## Scenario: 模型常驻复用

- **WHEN** 用户多次合成（不同文本/不同参考音频）
- **THEN** dots.tts 模型在 Python 进程内只加载一次（`backend/runtime.py` singleton）
- **AND** 每次 `/api/clone` 复用同一 `DotsTtsRuntime` 实例

## Scenario: 路径转换规则

- **WHEN** 前端拿到 Windows 路径（来自 Tauri `dialog.open()`）
- **THEN** 通过 `winToWsl2()` 规则转换：盘符小写 + `/mnt/<盘符>` + `\`→`/`
- **AND** 例：`D:\audio\ref.wav` → `/mnt/d/audio/ref.wav`；`C:\Users\ck\a.wav` → `/mnt/c/Users/ck/a.wav`
- **AND** 非 `^[A-Za-z]:[\\/]` 开头的路径（UNC、网络盘、相对路径）抛错
