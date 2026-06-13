const API_BASE =
  import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8765";

export type HealthStatus = "loading" | "ready" | "error";

export interface HealthResponse {
  status: HealthStatus;
  model: string;
  gpu: string | null;
  elapsed_ms: number;
  error: string | null;
}

export class ApiError extends Error {
  readonly kind: "network" | "http" | "parse";
  constructor(message: string, kind: "network" | "http" | "parse") {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
  }
}

export async function getHealth(): Promise<HealthResponse> {
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}/api/health`);
  } catch (e) {
    throw new ApiError(
      e instanceof Error ? e.message : "network error",
      "network",
    );
  }
  if (!resp.ok) {
    throw new ApiError(`HTTP ${resp.status}`, "http");
  }
  try {
    return (await resp.json()) as HealthResponse;
  } catch (e) {
    throw new ApiError(
      e instanceof Error ? e.message : "parse error",
      "parse",
    );
  }
}

export type CloneLanguage = "zh" | "none";

export interface CloneParams {
  text: string;
  promptAudioPath: string; // already WSL2-formatted
  promptText: string;
  numSteps?: number;
  guidanceScale?: number;
  language?: CloneLanguage;
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
    resp = await fetch(`${API_BASE}/api/clone`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (e) {
    throw new ApiError(
      e instanceof Error ? e.message : "network error",
      "network",
    );
  }
  if (!resp.ok) {
    let msg = `HTTP ${resp.status}`;
    try {
      const err = await resp.json();
      msg = typeof err.detail === "string" ? err.detail : msg;
    } catch {
      // body wasn't JSON, keep generic msg
    }
    throw new ApiError(msg, "http");
  }
  return await resp.blob();
}
