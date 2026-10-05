// 127.0.0.1 rather than localhost: browsers resolve localhost to ::1 first, and the dev
// server binds IPv4 only, so "localhost" intermittently fails to connect.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type HealthResponse = {
  status: "ok" | "degraded";
  service: string;
  environment: string;
  demo_mode: boolean;
  retention_hours: number;
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
  title_block: string[];
  section_headings: string[];
  signature_block: string[];
};

// --- Phase 2-4: risk label, statute evidence, plain-language explanation ---

export type RiskLabel = "GREEN" | "YELLOW" | "RED";

export type StatuteSupport = {
  entry_id: string;
  how_it_applies: string;
};

export type Explanation = {
  clause_id: string;
  risk_label: RiskLabel;
  document_says: string;
  concern: string;
  statute_support: StatuteSupport[];
  disclaimer: string;
};

export type AnalysedClause = {
  clause_id: string;
  text: string;
  risk_label: RiskLabel;
  risk_confidence: number;
  topic: string | null;
  retrieved_statutes: unknown[];
  explanation: Explanation | null;
  error: string | null;
};

export type CrossClause = {
  clause_id_a: string;
  clause_id_b: string;
  relationship_type: string;
  explanation: string;
};

export type DemoDocument = {
  filename: string;
  jurisdiction: string | null;
  clauses: AnalysedClause[];
  cross_clause: CrossClause[];
};

export type AnalysisSummary = {
  filename: string;
  jurisdiction: string | null;
  clause_count: number;
  connection_count: number;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, init);
  if (!response.ok) {
    const detail = await response
      .json()
      .then((b) => b.detail)
      .catch(() => null);
    throw new Error(detail ?? `Request failed with HTTP ${response.status}`);
  }
  return response.json();
}

export function fetchHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function listDocuments(): Promise<ParsedDocument[]> {
  return request<ParsedDocument[]>("/documents");
}

export function fetchDocument(id: string): Promise<ParsedDocument> {
  return request<ParsedDocument>(`/documents/${id}`);
}

export function listAnalyses(): Promise<AnalysisSummary[]> {
  return request<AnalysisSummary[]>("/analysis/documents");
}

export function fetchAnalysis(filename: string): Promise<DemoDocument> {
  return request<DemoDocument>(`/analysis/documents/${encodeURIComponent(filename)}`);
}

export function uploadDocument(file: File): Promise<ParsedDocument> {
  const body = new FormData();
  body.append("file", file);
  return request<ParsedDocument>("/documents", { method: "POST", body });
}
