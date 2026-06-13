# Design: single-continuation-clone

## 1. 技术决策

| 维度 | 选择 | 备选放弃 | 理由 |
|------|------|----------|------|
| 参考音频传递 | **Windows 路径直传**（前端转 WSL2 路径） | HTTP multipart 上传 / 预设 prompts 目录 | 零拷贝；dots.tts API 本来就吃文件路径；个人本地单用户 |
| 合成结果返回 | **POST 响应体直接 wav bytes**（`audio/wav`） | 后端存盘返 URL / 后端存盘返 WSL2 路径 | 后端无状态、试听与保存解耦、单段 < 30s 内存装得下 |
| 保存到磁盘 | **Tauri `dialog.save()` + `fs.writeBinaryFile()`**（不经后端） | 后端 copy 接口 / 浏览器 download | 与"路径直传"风格一致；用户用文件选择器选保存位置 |
| 合成流程 | **同步阻塞**（POST 等几十秒一次返） | SSE 流式 / 异步轮询 | YAGNI；单段不超过几十秒；接口与错误处理简单 |
| 默认参数 | **后端锁死 `num_steps=10, guidance_scale=1.2, language="zh"`**，UI 提供"高级"折叠面板调这三项 | 完全无 UI / 完整参数面板 | 满足"基本不调参"主诉求同时给高级用户逃生口 |
| seed | **去掉该概念** | API 包一层 torch.manual_seed | dots.tts 经 ODE 求解，本就不可严格复现；YAGNI |

### 关键决策 1：路径直传 + 前端做 Windows→WSL2 转换

dots.tts 的 `runtime.generate(prompt_audio_path=...)` 吃的是 WSL2 文件系统下的路径。前端是 Windows Tauri，用 Tauri `dialog.open()` 选文件得到的是 Windows 路径（`D:\audio\ref.wav`）。两者之间需要转换。

转换规则：
- 盘符 `C:` → `/mnt/c`，`D:` → `/mnt/d`（盘符小写）
- 反斜杠 `\` → 正斜杠 `/`
- 例：`D:\audio\ref.wav` → `/mnt/d/audio/ref.wav`

**边界**：只支持 `^[A-Za-z]:\\` 开头的本地盘路径。UNC 路径（`\\server\share`）、网络盘、`%USERPROFILE%` 等场景 v0.1 直接报"不支持的路径"。

### 关键决策 2：后端零落盘

合成结果不写 `outputs/`，直接 `soundfile.write(BytesIO, format="WAV")` 编码到内存 buffer，作为 HTTP 响应体返回。优点：
- 后端无状态、无垃圾文件
- 前端拿到 bytes 后用 Blob URL 试听，用 Tauri fs 直接写盘保存
- 试听与保存解耦（试听不强制保存，保存不强制经过后端）

### 关键决策 3：UI 高级折叠面板

`spec/requirements.md` 写"不做参数调节面板"，本变更做的是**有限暴露**：
- 默认锁死，UI 不展示
- 点"高级参数"折叠展开，可调 `num_steps` / `guidance_scale` / `language(zh|none)`
- 其他参数（`speaker_scale`、`ode_method`、`normalize_text`、`template_name`、`max_generate_length`）后端默认值固定，不暴露

同步修订 `spec/requirements.md` 反映此调整。

## 2. 项目结构

```
backend/
├── app.py                  # 改：注册 POST /api/clone 路由
├── runtime.py              # 不动（已就绪）
├── clone.py                # 新：合成 + wav 编码
├── paths.py                # 新：Windows → WSL2 路径转换 + 校验
└── requirements.txt        # 改：补 soundfile（如未装）

frontend/src/
├── App.tsx                 # 改：根据 health status 切到 ClonePage（ready 时）
├── api.ts                  # 改：加 cloneSynth() + 类型定义
├── paths.ts                # 新：Windows → WSL2 路径转换（前端侧）
├── pages/
│   └── ClonePage.tsx       # 新：单段克隆主页面
└── components/
    └── AdvancedParams.tsx  # 新：折叠面板（num_steps / guidance / language）

src-tauri/
├── Cargo.toml              # 改：加 tauri-plugin-dialog + tauri-plugin-fs
├── capabilities/default.json  # 改：授予 dialog:allow-open / dialog:allow-save / fs:allow-write-binary-file + scope
└── tauri.conf.json         # 改：plugins 节
```

## 3. 模块设计

### `backend/paths.py` — WSL2 路径校验

```python
import re
from pathlib import Path

WIN_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")

def wsl2_to_win(path: str) -> str:
    """WSL2 路径反向转 Windows（错误提示用，不主流程）。"""

def win_to_wsl2(path: str) -> str:
    """Windows 路径转 WSL2 路径。不合法抛 ValueError。"""
    if not WIN_PATH_RE.match(path):
        raise ValueError(f"不支持的路径格式（仅本地盘 X:\\...）：{path}")
    drive = path[0].lower()
    rest = path[2:].replace("\\", "/")
    return f"/mnt/{drive}{rest}"

def validate_prompt_audio(wsl2_path: str) -> None:
    """校验：必须以 /mnt/ 开头 + 文件存在 + 扩展名是音频。"""
    if not wsl2_path.startswith("/mnt/"):
        raise ValueError("参考音频路径必须在 /mnt/ 下")
    p = Path(wsl2_path)
    if not p.is_file():
        raise FileNotFoundError(f"参考音频文件不存在：{wsl2_path}")
    if p.suffix.lower() not in {".wav", ".mp3", ".flac", ".ogg", ".m4a"}:
        raise ValueError(f"不支持的音频格式：{p.suffix}")
```

### `backend/clone.py` — 合成 + wav 编码

```python
import io
from typing import Any

from fastapi import HTTPException
import soundfile as sf

from .runtime import get_runtime
from .paths import validate_prompt_audio

DEFAULT_NUM_STEPS = 10
DEFAULT_GUIDANCE = 1.2
DEFAULT_LANGUAGE = "zh"

def synthesize_clone(
    *,
    text: str,
    prompt_audio_path: str,   # 已是 WSL2 路径
    prompt_text: str,
    num_steps: int = DEFAULT_NUM_STEPS,
    guidance_scale: float = DEFAULT_GUIDANCE,
    language: str = DEFAULT_LANGUAGE,
) -> bytes:
    """返回 wav bytes（48kHz mono）。失败抛 HTTPException。"""
    # 1. 校验音频路径
    try:
        validate_prompt_audio(prompt_audio_path)
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=f"参考音频无效：{e}")

    # 2. 校验文本
    if not text.strip():
        raise HTTPException(status_code=422, detail="目标文本不能为空")
    if not prompt_text.strip():
        raise HTTPException(status_code=422, detail="参考转录不能为空")

    # 3. 调 dots.tts
    runtime = get_runtime()
    try:
        result = runtime.generate(
            text=text,
            prompt_audio_path=prompt_audio_path,
            prompt_text=prompt_text,
            language=language if language != "none" else None,
            num_steps=num_steps,
            guidance_scale=guidance_scale,
        )
    except ValueError as e:
        # 主要是 max_generate_length 超限
        raise HTTPException(status_code=413, detail=f"文本过长或不被模型接受：{e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"合成失败：{type(e).__name__}: {e}")

    # 4. audio Tensor → wav bytes
    audio = result["audio"]
    sample_rate = result["sample_rate"]
    # audio shape: (1, N) or (N,) — soundfile 要 (channels, frames) 或 1D
    if audio.ndim == 2:
        audio = audio.squeeze(0)
    audio_np = audio.cpu().float().numpy()

    buf = io.BytesIO()
    sf.write(buf, audio_np, sample_rate, format="WAV", subtype="PCM_16")
    return buf.getvalue()
```

### `backend/app.py` — FastAPI 路由

新增：

```python
from pydantic import BaseModel, Field
from .clone import synthesize_clone

class CloneRequest(BaseModel):
    text: str = Field(..., min_length=1)
    prompt_audio_path: str = Field(..., min_length=1)
    prompt_text: str = Field(..., min_length=1)
    num_steps: int = Field(10, ge=1, le=100)
    guidance_scale: float = Field(1.2, ge=0.0, le=10.0)
    language: str = Field("zh", pattern="^(zh|none)$")

@app.post("/api/clone")
def clone(req: CloneRequest):
    wav_bytes = synthesize_clone(
        text=req.text,
        prompt_audio_path=req.prompt_audio_path,
        prompt_text=req.prompt_text,
        num_steps=req.num_steps,
        guidance_scale=req.guidance_scale,
        language=req.language,
    )
    return Response(content=wav_bytes, media_type="audio/wav")
```

### `frontend/src/paths.ts` — Windows → WSL2 转换

```typescript
const WIN_PATH_RE = /^[A-Za-z]:[\\/]/;

export function winToWsl2(path: string): string {
  if (!WIN_PATH_RE.test(path)) {
    throw new Error(`不支持的路径（仅本地盘 X:\\...）：${path}`);
  }
  const drive = path[0].toLowerCase();
  const rest = path.slice(2).replace(/\\/g, "/");
  return `/mnt/${drive}${rest}`;
}
```

### `frontend/src/api.ts` — 加 cloneSynth

```typescript
export interface CloneParams {
  text: string;
  promptAudioPath: string;  // 已是 WSL2 路径
  promptText: string;
  numSteps?: number;
  guidanceScale?: number;
  language?: "zh" | "none";
}

export async function cloneSynth(params: CloneParams): Promise<Blob> {
  const body = {
    text: params.text,
    prompt_audio_path: params.promptAudioPath,
    prompt_text: params.promptText,
    num_steps: params.numSteps ?? 10,
    guidance_scale: params.guidanceScale ?? 1.2,
    language: params.language ?? "zh",
  };
  let resp: Response;
  try {
    resp = await fetch(`${BASE}/api/clone`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    throw new ApiError(`网络错误：${(e as Error).message}`, "network");
  }
  if (!resp.ok) {
    let msg = `HTTP ${resp.status}`;
    try {
      const err = await resp.json();
      msg = err.detail || msg;
    } catch {}
    throw new ApiError(msg, "http");
  }
  return await resp.blob();
}
```

### `frontend/src/pages/ClonePage.tsx` — 主页面

- 状态：`text` / `promptWinPath` / `promptText` / `advancedParams` / `status(idle|synthing|done|error)` / `errorMsg` / `audioBlobUrl` / `savedMsg`
- 文件选择：`import { open } from "@tauri-apps/plugin-dialog"` → `open({ filters: [{ name: "音频", extensions: ["wav","mp3","flac","ogg","m4a"] }] })` → 拿 Windows 路径，`winToWsl2` 转换
- 合成：调 `cloneSynth()` → `URL.createObjectURL(blob)` 喂 `<audio>`
- 保存：`save({ defaultPath: "clone.wav" })` 拿 Windows 路径 → `writeBinaryFile(target, new Uint8Array(arrayBuffer))`
- 错误：try/catch 包 `cloneSynth` 与 `writeBinaryFile`，错误信息 inline 显示

### `frontend/src/components/AdvancedParams.tsx` — 折叠面板

- `<details>` 原生折叠
- 三个输入：`num_steps`（number）/ `guidance_scale`（number, step=0.1）/ `language`（select: zh/none）
- onChange 回调父组件

### `src-tauri/capabilities/default.json` — 权限

```json
{
  "permissions": [
    "core:default",
    "dialog:allow-open",
    "dialog:allow-save",
    "fs:allow-write-binary-file",
    "fs:scope"
  ]
}
```

`fs:scope` 默认是 `$HOME/*` 等几个安全目录。v0.1 dev 阶段先放宽到 `**` 允许写任意位置（保存位置用户选），后续 package-release 再收紧。

## 4. 端到端数据流

```
[选文件]
  Tauri dialog.open() → "D:\\audio\\ref.wav"
  winToWsl2() → "/mnt/d/audio/ref.wav"
  UI 显示 "ref.wav ✓"

[输入文本/转录] (本地状态)

[可选: 调高级参数]

[点合成]
  cloneSynth({ text, prompt_audio_path, prompt_text, ... })
    → POST /api/clone (json body)
      → backend/clone.py:synthesize_clone()
        → validate_prompt_audio()
        → runtime.generate()
        → soundfile.write(BytesIO)
        → return Response(wav_bytes, audio/wav)
    → resp.blob()
  UI: URL.createObjectURL(blob) → <audio src> 自动可播

[点保存到...]
  Tauri dialog.save({ defaultPath: "clone.wav" }) → "D:\\out\\clone.wav"
  Tauri fs.writeBinaryFile(target, uint8array)
  UI: 显示 "已保存到 D:\\out\\clone.wav"
```

## 5. 风险与权衡

### 风险 1：Tauri fs scope 限制

- **风险**：Tauri 2.x 的 fs plugin 默认只允许写 `$HOME`、`$APPDATA` 等几个目录，写 `D:\out\clone.wav` 可能被拒
- **缓解**：dev 阶段 capabilities 里把 `fs:scope` 放宽到 `**`；package-release 任务再考虑收紧策略

### 风险 2：dots.tts max_generate_length 限制

- **风险**：`max_generate_length=500` patch 大约对应几十秒音频，长文本会抛 ValueError
- **缓解**：后端抓 ValueError 返 413，UI 提示"文本过长，建议拆分（批量合成在后续 task）"

### 风险 3：路径转换边界情况

- **风险**：UNC `\\server\share`、网络盘、`%USERPROFILE%` 转不出来
- **缓解**：v0.1 显式只接受 `^[A-Za-z]:[\\/]` 本地盘路径，其他直接抛"不支持的路径格式"；UI 错误提示明确

### 风险 4：合成 30s 阻塞期间用户感知

- **风险**：同步阻塞，用户不知道进度
- **缓解**：UI"合成中"loading + 文案"合成中（可能需要 10~30 秒）..."；不改架构（流式留待后续）

### 风险 5：soundfile 是否已在 dots_tts env 里

- **风险**：依赖 soundfile 编码 wav，需确认 dots.tts 装时已带
- **缓解**：执行阶段先 `python -c "import soundfile"` 验证，缺则 `pip install soundfile`

## 6. 待定项

- Tauri fs scope 放宽到 `**` 还是给具体白名单——dev 阶段先 `**`，package-release 再定
- 合成完成是否自动播放——v0.1 默认不自动播放，用户点 `<audio>` play 按钮
- 同段文本二次合成结果差异（ODE 不可复现）——不做去重缓存，每次重新合成

## 7. 待提升到 `spec/design.md` 的条目（archive 时处理）

- ✅ 合成 API 路径：`POST /api/clone` 同步返回 wav bytes
- ✅ 默认合成参数：`num_steps=10, guidance_scale=1.2, language="zh"`
- ✅ 参考音频传递：Windows 路径直传 + 前端转 WSL2

剩余 `spec/design.md` §7 待定项继续保留：音色库格式、目标 OS、默认参数已破例先定（与原"single-continuation-clone 启动前定"对齐）。
