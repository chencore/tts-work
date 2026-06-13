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
