const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type HealthResponse = {
  status: "ok" | "degraded";
  service: string;
  environment: string;
  database: {
    connected: boolean;
    server_version: string | null;
    error: string | null;
  };
};

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with HTTP ${response.status}`);
  }
  return response.json();
}
