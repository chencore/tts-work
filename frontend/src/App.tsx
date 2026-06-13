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

  return (
    <main className="app">
      <h1>tts-work</h1>
      {view.kind === "waiting" && (
        <p className="status waiting">等待后端启动...</p>
      )}
      {view.kind === "loading" && (
        <p className="status loading">
          模型加载中（{(view.elapsedMs / 1000).toFixed(1)}s）
        </p>
      )}
      {view.kind === "ready" && (
        <>
          <p className="status ready">
            ✓ 就绪 · GPU: {view.gpu ?? "未知"} · 模型: {view.model}
          </p>
          <ClonePage />
        </>
      )}
      {view.kind === "error" && (
        <p className="status error">后端错误：{view.message}</p>
      )}
    </main>
  );
}
