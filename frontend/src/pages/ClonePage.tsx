import { useState } from "react";
import { open, save } from "@tauri-apps/plugin-dialog";
import { writeFile } from "@tauri-apps/plugin-fs";

import { ApiError, cloneSynth } from "../api";
import AdvancedParams, {
  type AdvancedParamValues,
} from "../components/AdvancedParams";
import { winToWsl2 } from "../paths";

type SynthStatus =
  | { kind: "idle" }
  | { kind: "synthing" }
  | { kind: "done"; blobUrl: string }
  | { kind: "error"; message: string };

const DEFAULT_ADVANCED: AdvancedParamValues = {
  numSteps: 10,
  guidanceScale: 1.2,
  language: "zh",
};

export default function ClonePage() {
  const [text, setText] = useState("");
  const [promptWinPath, setPromptWinPath] = useState<string | null>(null);
  const [promptText, setPromptText] = useState("");
  const [advanced, setAdvanced] = useState<AdvancedParamValues>(DEFAULT_ADVANCED);
  const [status, setStatus] = useState<SynthStatus>({ kind: "idle" });
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  const canSynth =
    text.trim() && promptWinPath && promptText.trim() && status.kind !== "synthing";

  async function handlePickAudio() {
    try {
      const picked = await open({
        filters: [{ name: "音频", extensions: ["wav", "mp3", "flac", "ogg", "m4a"] }],
      });
      if (typeof picked === "string") {
        setPromptWinPath(picked);
      }
    } catch (e) {
      setStatus({
        kind: "error",
        message: `选择文件失败：${e instanceof Error ? e.message : String(e)}`,
      });
    }
  }

  async function handleSynth() {
    if (!promptWinPath) return;
    setSavedMsg(null);
    setStatus({ kind: "synthing" });
    let wsl2Path: string;
    try {
      wsl2Path = winToWsl2(promptWinPath);
    } catch (e) {
      setStatus({
        kind: "error",
        message: e instanceof Error ? e.message : String(e),
      });
      return;
    }
    try {
      const blob = await cloneSynth({
        text,
        promptAudioPath: wsl2Path,
        promptText,
        numSteps: advanced.numSteps,
        guidanceScale: advanced.guidanceScale,
        language: advanced.language,
      });
      // revoke previous blob url if any
      if (status.kind === "done") {
        URL.revokeObjectURL(status.blobUrl);
      }
      const blobUrl = URL.createObjectURL(blob);
      setStatus({ kind: "done", blobUrl });
    } catch (e) {
      const msg =
        e instanceof ApiError
          ? `${e.kind === "network" ? "网络错误" : "后端错误"}：${e.message}`
          : e instanceof Error
            ? e.message
            : String(e);
      setStatus({ kind: "error", message: msg });
    }
  }

  async function handleSave() {
    if (status.kind !== "done") return;
    try {
      const target = await save({ defaultPath: "clone.wav" });
      if (!target) return;
      const buf = await (await fetch(status.blobUrl)).arrayBuffer();
      await writeFile(target, new Uint8Array(buf));
      setSavedMsg(`已保存到 ${target}`);
    } catch (e) {
      setSavedMsg(
        `保存失败：${e instanceof Error ? e.message : String(e)}`,
      );
    }
  }

  const fileName = promptWinPath
    ? promptWinPath.split(/[\\/]/).pop()
    : null;

  return (
    <section className="clone-page">
      <h2>单段克隆</h2>

      <label className="field">
        <span className="field-label">目标文本</span>
        <textarea
          rows={4}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="请输入要合成的中文文本..."
        />
      </label>

      <div className="field">
        <span className="field-label">参考音频</span>
        {fileName && (
          <div className="audio-file">
            <div className="audio-file-icon">♪</div>
            <span className="audio-file-name">{fileName}</span>
            <span className="audio-file-check">✓</span>
          </div>
        )}
        <button
          type="button"
          className="btn-secondary"
          onClick={handlePickAudio}
        >
          {fileName ? "更换文件" : "选择文件"}
        </button>
      </div>

      <label className="field">
        <span className="field-label">参考转录</span>
        <textarea
          rows={3}
          value={promptText}
          onChange={(e) => setPromptText(e.target.value)}
          placeholder="输入参考音频对应的文本..."
        />
      </label>

      <AdvancedParams value={advanced} onChange={setAdvanced} />

      <div className="actions">
        <button
          type="button"
          onClick={handleSynth}
          disabled={!canSynth}
        >
          {status.kind === "synthing" ? "合成中（可能需 10~30 秒）..." : "合成"}
        </button>
      </div>

      {status.kind === "error" && (
        <p className="error">{status.message}</p>
      )}

      {status.kind === "done" && (
        <div className="result">
          <audio className="result-audio" src={status.blobUrl} controls />
          <div className="result-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={handleSave}
            >
              保存到...
            </button>
            {savedMsg && <p className="hint">{savedMsg}</p>}
          </div>
        </div>
      )}
    </section>
  );
}
