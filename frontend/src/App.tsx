import { useEffect, useState } from "react";
import { ApiError, getHealth } from "./api";
import type { HealthResponse } from "./api";
import ClonePage from "./pages/ClonePage";

type View =
  | { kind: "waiting" }
  | { kind: "loading"; elapsedMs: number }
  | { kind: "ready"; gpu: string | null; model: string }
  | { kind: "error"; message: string };

function fromHealth(h: HealthResponse): View {
  if (h.status === "ready") {
    return { kind: "ready", gpu: h.gpu, model: h.model };
  }
  if (h.status === "error") {
    return { kind: "error", message: h.error ?? "unknown error" };
  }
  return { kind: "loading", elapsedMs: h.elapsed_ms };
}

function fromError(e: unknown): View {
  if (e instanceof ApiError && e.kind === "network") {
    return { kind: "waiting" };
  }
  return {
    kind: "error",
    message: e instanceof Error ? e.message : String(e),
  };
}

export default function App() {
  const [view, setView] = useState<View>({ kind: "waiting" });

  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      try {
        const h = await getHealth();
        if (!cancelled) setView(fromHealth(h));
      } catch (e) {
        if (!cancelled) setView(fromError(e));
      }
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const statusText = (() => {
    if (view.kind === "waiting") return "等待后端启动";
    if (view.kind === "loading")
      return `加载模型 ${(view.elapsedMs / 1000).toFixed(1)}s`;
    if (view.kind === "ready")
      return `就绪 · ${view.gpu ?? "未知 GPU"}`;
    return "后端错误";
  })();

  return (
    <main className="app">
      <header className="app-header">
        <h1>tts-work</h1>
        <span className={`status ${view.kind}`}>
          <span className="status-dot" />
          {statusText}
        </span>
      </header>

      {view.kind === "waiting" && (
        <div className="app-message">等待后端启动...</div>
      )}
      {view.kind === "loading" && (
        <div className="app-message">
          模型加载中（{(view.elapsedMs / 1000).toFixed(1)}s）
        </div>
      )}
      {view.kind === "ready" && <ClonePage />}
      {view.kind === "error" && (
        <div className="app-message">后端错误：{view.message}</div>
      )}
    </main>
  );
}
