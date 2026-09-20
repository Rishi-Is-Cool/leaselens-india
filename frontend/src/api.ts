// 127.0.0.1 rather than localhost: browsers resolve localhost to ::1 first, and the dev
// server binds IPv4 only, so "localhost" intermittently fails to connect.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

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

export type Clause = {
  clause_id: string;
  section_heading: string | null;
  text: string;
  order: number;
};

export type ParsedDocument = {
  id: string;
  filename: string;
  content_type: string;
  page_count: number;
  extraction_method: "text" | "ocr" | "mixed";
  clause_count: number;
  clauses: Clause[];
};

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE}/health`);
  if (!response.ok) {
    throw new Error(`Health check failed with HTTP ${response.status}`);
  }
  return response.json();
}

export async function uploadDocument(file: File): Promise<ParsedDocument> {
  const body = new FormData();
  body.append("file", file);

  const response = await fetch(`${API_BASE}/documents`, { method: "POST", body });
  if (!response.ok) {
    const detail = await response
      .json()
      .then((b) => b.detail)
      .catch(() => null);
    throw new Error(detail ?? `Upload failed with HTTP ${response.status}`);
  }
  return response.json();
}
