import { useEffect, useRef, useState } from "react";
import {
  fetchHealth,
  uploadDocument,
  type HealthResponse,
  type ParsedDocument,
} from "./api";

type Upload =
  | { phase: "idle" }
  | { phase: "parsing"; filename: string }
  | { phase: "failed"; message: string }
  | { phase: "parsed"; document: ParsedDocument };

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [upload, setUpload] = useState<Upload>({ phase: "idle" });
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchHealth().then(setHealth).catch(() => setHealth(null));
  }, []);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setUpload({ phase: "parsing", filename: file.name });
    try {
      setUpload({ phase: "parsed", document: await uploadDocument(file) });
    } catch (error) {
      setUpload({ phase: "failed", message: (error as Error).message });
    }
  }

  const dbOk = health?.database.connected ?? false;

  return (
    <main className="shell">
      <header className="masthead">
        <div>
          <h1>LeaseLens</h1>
          <p className="tagline">Clause segmentation check — Phase 1</p>
        </div>
        <span className={`pill ${dbOk ? "pill-good" : "pill-bad"}`}>
          {health === null
            ? "API unreachable"
            : dbOk
              ? `API ok · Postgres ${health.database.server_version}`
              : "API up · database down"}
        </span>
      </header>

      <section
        className={`dropzone ${dragging ? "dropzone-active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          void handleFile(e.dataTransfer.files[0]);
        }}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,image/png,image/jpeg"
          hidden
          onChange={(e) => void handleFile(e.target.files?.[0])}
        />
        <strong>Drop a lease here</strong>
        <span className="muted">or click to choose — PDF, PNG, or JPEG</span>
      </section>

      {upload.phase === "parsing" && (
        <p className="notice">Parsing {upload.filename}…</p>
      )}

      {upload.phase === "failed" && (
        <p className="notice notice-bad">{upload.message}</p>
      )}

      {upload.phase === "parsed" && <Result document={upload.document} />}
    </main>
  );
}

function Result({ document }: { document: ParsedDocument }) {
  return (
    <>
      <section className="summary">
        <Stat label="File" value={document.filename} />
        <Stat label="Pages" value={String(document.page_count)} />
        <Stat
          label="Extraction"
          value={document.extraction_method === "text" ? "embedded text" : document.extraction_method}
        />
        <Stat label="Clauses" value={String(document.clause_count)} />
      </section>

      <ol className="clauses">
        {document.clauses.map((clause) => (
          <li key={clause.clause_id} className="clause">
            <div className="clause-meta">
              <span className="clause-id">{clause.clause_id}</span>
              {clause.section_heading ? (
                <span className="clause-heading">{clause.section_heading}</span>
              ) : (
                <span className="clause-heading clause-heading-none">no heading</span>
              )}
            </div>
            <p className="clause-text">{clause.text}</p>
          </li>
        ))}
      </ol>

      <p className="disclaimer">
        This screen shows text extracted from the document as-is. It is not legal advice.
        Laws vary by location and change over time — verify with a qualified professional
        before acting.
      </p>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  );
}
