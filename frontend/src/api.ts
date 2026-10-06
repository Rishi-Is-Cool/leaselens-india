// 127.0.0.1 rather than localhost: browsers resolve localhost to ::1 first, and the dev
// server binds IPv4 only, so "localhost" intermittently fails to connect.
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

// The hosted site has no backend: it replays saved analyses bundled with the build, so it
// cannot sleep, run out of LLM quota, or expose anyone's uploads. Set by .env.production.
export const STATIC_DEMO = import.meta.env.VITE_STATIC_DEMO === "true";

export type HealthResponse = {
  status: "ok" | "degraded";
  service: string;
  environment: string;
  demo_mode: boolean;
  retention_hours: number;
  llm_configured: boolean;
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

export type Statute = {
  entry_id: string;
  citation: string;
  excerpt_text: string;
  source_url: string;
  last_verified_date: string;
};

export type AnalysedClause = {
  clause_id: string;
  section_heading?: string | null;
  text: string;
  risk_label: RiskLabel;
  risk_confidence: number;
  topic: string | null;
  retrieved_statutes: Statute[];
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
  explained_count: number;
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

type BundledDocument = Omit<AnalysisSummary, "filename"> & Pick<DemoDocument, "clauses" | "cross_clause">;

let bundled: Promise<Record<string, BundledDocument>> | null = null;

function loadBundled(): Promise<Record<string, BundledDocument>> {
  bundled ??= fetch("/demo-analysis.json").then((response) => {
    if (!response.ok) throw new Error(`Saved analyses could not be loaded (HTTP ${response.status})`);
    return response.json();
  });
  return bundled;
}

export async function listAnalyses(): Promise<AnalysisSummary[]> {
  if (!STATIC_DEMO) return request<AnalysisSummary[]>("/analysis/documents");
  const documents = await loadBundled();
  return Object.entries(documents).map(([filename, d]) => ({
    filename,
    jurisdiction: d.jurisdiction,
    clause_count: d.clause_count,
    explained_count: d.explained_count,
    connection_count: d.connection_count,
  }));
}

export async function fetchAnalysis(filename: string): Promise<DemoDocument> {
  if (!STATIC_DEMO) return request<DemoDocument>(`/analysis/documents/${encodeURIComponent(filename)}`);
  const document = (await loadBundled())[filename];
  if (!document) throw new Error("No saved analysis was found for this filename.");
  return { filename, jurisdiction: document.jurisdiction, clauses: document.clauses, cross_clause: document.cross_clause };
}

export function uploadDocument(file: File): Promise<ParsedDocument> {
  const body = new FormData();
  body.append("file", file);
  return request<ParsedDocument>("/documents", { method: "POST", body });
}

// --- Live analysis of an uploaded document (Phases 2-4 run on demand) ---

export type JurisdictionHint = {
  jurisdiction: string | null;
  evidence: string[];
  unsupported_state: string | null;
  ambiguous: boolean;
};

export type LiveAnalysis = {
  document_id: string;
  filename: string;
  supported_jurisdictions: string[];
  jurisdiction_hint: JurisdictionHint;
  llm_configured: boolean;
  status: "not_started" | "running" | "done" | "failed";
  jurisdiction: string | null;
  explanations_available: boolean;
  progress: { done: number; total: number };
  result: { clauses: AnalysedClause[]; cross_clause: CrossClause[] } | null;
  error: string | null;
};

export function fetchLiveAnalysis(documentId: string): Promise<LiveAnalysis> {
  return request<LiveAnalysis>(`/documents/${documentId}/analysis`);
}

export function startLiveAnalysis(documentId: string, jurisdiction: string | null): Promise<LiveAnalysis> {
  return request<LiveAnalysis>(`/documents/${documentId}/analysis`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ jurisdiction }),
  });
}
