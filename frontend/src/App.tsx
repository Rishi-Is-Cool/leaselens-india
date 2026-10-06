import { useEffect, useRef, useState } from "react";
import { LiveAnalysisPanel } from "./LiveAnalysis";
import {
  fetchAnalysis,
  fetchDocument,
  fetchHealth,
  listAnalyses,
  listDocuments,
  uploadDocument,
  STATIC_DEMO,
  type AnalysedClause,
  type AnalysisSummary,
  type DemoDocument,
  type HealthResponse,
  type LiveAnalysis,
  type ParsedDocument,
} from "./api";

type Upload =
  | { phase: "idle" }
  | { phase: "parsing"; filename: string }
  | { phase: "failed"; message: string }
  | { phase: "parsed" };

export default function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [library, setLibrary] = useState<ParsedDocument[]>([]);
  const [selected, setSelected] = useState<ParsedDocument | null>(null);
  const [analysis, setAnalysis] = useState<DemoDocument | null>(null);
  const [upload, setUpload] = useState<Upload>({ phase: "idle" });
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function refreshLibrary() {
    try {
      setLibrary(await listDocuments());
    } catch {
      setLibrary([]);
    }
  }

  useEffect(() => {
    if (!STATIC_DEMO) {
      fetchHealth().then(setHealth).catch(() => setHealth(null));
      void refreshLibrary();
    }
    // Surface the pre-analysed sample immediately, so the review panel opens on the
    // Phase 4 output rather than an empty state.
    listAnalyses()
      .then((list) => (list.length ? fetchAnalysis(list[0].filename) : null))
      .then(setAnalysis)
      .catch(() => setAnalysis(null));
  }, []);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setUpload({ phase: "parsing", filename: file.name });
    try {
      const parsed = await uploadDocument(file);
      // The uploaded lease is reviewed live; a saved sample with the same filename is a
      // different document's result and must not stand in for it.
      setSelected(parsed);
      setAnalysis(null);
      setUpload({ phase: "parsed" });
      await refreshLibrary();
    } catch (error) {
      setUpload({ phase: "failed", message: (error as Error).message });
    }
  }

  async function openDocument(id: string) {
    try {
      setSelected(await fetchDocument(id));
      setAnalysis(null);
      setUpload({ phase: "parsed" });
    } catch (error) {
      setUpload({ phase: "failed", message: (error as Error).message });
    }
  }

  async function openAnalysis(filename: string) {
    try {
      setAnalysis(await fetchAnalysis(filename));
      setSelected(null);
      setUpload({ phase: "parsed" });
    } catch (error) {
      setUpload({ phase: "failed", message: (error as Error).message });
    }
  }

  const dbOk = health?.database.connected ?? false;

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="LeaseLens home">
          <span className="brand-mark">L</span>
          <span>LeaseLens</span>
        </a>
        <div className={`status ${STATIC_DEMO || dbOk ? "status-ready" : "status-waiting"}`}>
          <i />
          {STATIC_DEMO
            ? "Saved demo"
            : health === null
              ? "Connecting to workspace"
              : dbOk
                ? "Workspace ready"
                : "Database offline"}
        </div>
      </header>

      <main className="workspace">
        <section className="hero">
          <div>
            <span className="eyebrow">LEASE REVIEW WORKSPACE</span>
            <h1>Understand what your lease actually says.</h1>
            <p>
              {STATIC_DEMO
                ? "Browse real-format sample leases: every clause is flagged by how much attention it deserves, explained in plain language, and checked against the rental law where we have it."
                : "Upload a lease to pull out every clause, see which ones are worth a closer look, and read a plain-language explanation of each."}
            </p>
          </div>
          <div className="hero-note">
            <span>{STATIC_DEMO ? "Sample leases only" : "Private by design"}</span>
            <strong>
              {STATIC_DEMO
                ? "Nothing you do here is uploaded or stored"
                : `Files are removed after ${health?.retention_hours ?? 24} hours`}
            </strong>
          </div>
        </section>

        {STATIC_DEMO && (
          <aside className="demo-banner">
            <strong>Saved demo of a work in progress.</strong> These are synthetic sample
            leases reviewed ahead of time, so there is nothing to upload on this page. The
            full app, which reads a lease you upload, runs locally. Maharashtra is the
            most complete example. AI-assisted information only, not legal advice.
          </aside>
        )}

        {!STATIC_DEMO && health?.demo_mode && (
          <aside className="demo-banner">
            <strong>Demo workspace.</strong> This version extracts lease text and reviews
            it with AI assistance; it does not provide legal advice.
          </aside>
        )}

        <section className="dashboard">
          <aside className="library">
            <div className="library-heading">
              <div>
                <span className="eyebrow">ANALYSED SAMPLES</span>
                <h2>Reviewed leases</h2>
              </div>
            </div>
            <AnalysisLibrary onOpen={openAnalysis} current={analysis?.filename ?? null} />

            {!STATIC_DEMO && (<>
            <div className="library-heading">
              <div>
                <span className="eyebrow">YOUR DOCUMENTS</span>
                <h2>Recent uploads</h2>
              </div>
              <span className="document-count">{library.length}</span>
            </div>
            <div className="document-list">
              {library.length ? (
                library.map((doc) => (
                  <button
                    key={doc.id}
                    className={`document-item ${selected?.id === doc.id ? "document-item-active" : ""}`}
                    onClick={() => void openDocument(doc.id)}
                  >
                    <span className="document-icon">▤</span>
                    <span>
                      <strong>{doc.filename}</strong>
                      <small>
                        {doc.page_count} page{doc.page_count === 1 ? "" : "s"} ·{" "}
                        {doc.clause_count} clauses
                      </small>
                    </span>
                  </button>
                ))
              ) : (
                <p className="empty-library">Your uploaded lease reviews will appear here.</p>
              )}
            </div>
            </>)}
          </aside>

          <section className="review-panel">
            {analysis ? (
              <AnalysisResult document={analysis} />
            ) : selected ? (
              <DocumentReview
                key={selected.id}
                document={selected}
                onUploadAnother={() => inputRef.current?.click()}
              />
            ) : STATIC_DEMO ? (
              <p className="notice">Loading the saved review…</p>
            ) : (
              <UploadCard
                dragging={dragging}
                inputRef={inputRef}
                upload={upload}
                onFile={handleFile}
                onDragging={setDragging}
              />
            )}
            {!STATIC_DEMO && (
              <input
                ref={inputRef}
                type="file"
                accept="application/pdf,image/png,image/jpeg"
                hidden
                onChange={(e) => void handleFile(e.target.files?.[0])}
              />
            )}
          </section>
        </section>
      </main>

      <footer>
        LeaseLens organizes document text for review. It is not legal advice.
      </footer>
    </div>
  );
}

function AnalysisLibrary({
  onOpen,
  current,
}: {
  onOpen: (filename: string) => void;
  current: string | null;
}) {
  const [items, setItems] = useState<AnalysisSummary[]>([]);

  useEffect(() => {
    listAnalyses().then(setItems).catch(() => setItems([]));
  }, []);

  if (!items.length) return <p className="empty-library">No analysed samples found.</p>;

  return (
    <div className="document-list">
      {items.map((item) => (
        <button
          key={item.filename}
          className={`document-item demo-document ${current === item.filename ? "document-item-active" : ""}`}
          onClick={() => onOpen(item.filename)}
        >
          <span className="document-icon">◆</span>
          <span>
            <strong>{item.filename.replace(/^\d+_/, "").replace(/\.pdf$/i, "")}</strong>
            <small>
              {item.jurisdiction ?? "Jurisdiction not supported yet"} ·{" "}
              {item.explained_count === item.clause_count
                ? "fully explained"
                : item.explained_count === 0
                  ? "risk labels only"
                  : `${item.explained_count}/${item.clause_count} explained`}
            </small>
          </span>
        </button>
      ))}
    </div>
  );
}

function UploadCard({
  dragging,
  inputRef,
  upload,
  onFile,
  onDragging,
}: {
  dragging: boolean;
  inputRef: React.RefObject<HTMLInputElement | null>;
  upload: Upload;
  onFile: (file: File | undefined) => void;
  onDragging: (value: boolean) => void;
}) {
  return (
    <div className="upload-empty">
      <div className="review-intro">
        <span className="eyebrow">NEW REVIEW</span>
        <h2>Start with a lease document</h2>
        <p>We'll pull out the important sections so they are easier to read.</p>
      </div>
      <div
        className={`dropzone ${dragging ? "dropzone-active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          onDragging(true);
        }}
        onDragLeave={() => onDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          onDragging(false);
          onFile(e.dataTransfer.files[0]);
        }}
        onClick={() => inputRef.current?.click()}
      >
        <span className="upload-icon">↑</span>
        <strong>Drop your lease here</strong>
        <span>
          or <u>browse files</u> from your computer
        </span>
        <small>PDF, PNG, or JPG · up to 20 MB</small>
      </div>
      {upload.phase === "parsing" && (
        <p className="notice">
          Reading <strong>{upload.filename}</strong>…
        </p>
      )}
      {upload.phase === "failed" && <p className="notice notice-bad">{upload.message}</p>}
    </div>
  );
}

function AnalysisResult({
  document,
  live,
}: {
  document: DemoDocument;
  live?: { explanationsAvailable: boolean; onChangeState: () => void };
}) {
  const counts = document.clauses.reduce(
    (acc, clause) => ({ ...acc, [clause.risk_label]: (acc[clause.risk_label] ?? 0) + 1 }),
    {} as Record<string, number>,
  );

  const unexplained = document.clauses.filter((c) => !c.explanation).length;

  return (
    <div className="result analysis-result">
      <div className="result-header">
        <div>
          <span className="eyebrow">{live ? "YOUR LEASE · LIVE REVIEW" : "LEASE ANALYSIS"}</span>
          <h2>{document.filename}</h2>
          <p>
            {document.jurisdiction
              ? `Checked against ${document.jurisdiction} rental law`
              : "No state rental law checked"}{" "}
            · {document.clauses.length} clauses reviewed
          </p>
        </div>
        {live ? (
          <button className="secondary-button" onClick={live.onChangeState}>
            Change state &amp; re-run
          </button>
        ) : (
          <span className="demo-chip">Analysis ready</span>
        )}
      </div>

      {live && !live.explanationsAvailable && (
        <p className="notice">
          Risk levels below come from LeaseLens's offline model, which is less accurate than
          the full AI review. Plain-language explanations need an AI provider, which isn't set
          up on this server yet — the matching rental law is still shown where we hold it.
        </p>
      )}

      {live && live.explanationsAvailable && unexplained > 0 && (
        <p className="notice">
          Plain-language explanations could not be generated for {unexplained} of{" "}
          {document.clauses.length} clauses (the AI provider may have hit its daily limit).
        </p>
      )}

      {!live && unexplained > 0 && (
        <p className="notice">
          {unexplained === document.clauses.length
            ? "This saved review has risk labels only — plain-language explanations were not generated for it."
            : `Plain-language explanations are missing for ${unexplained} of ${document.clauses.length} clauses in this saved review.`}
        </p>
      )}

      <div className="risk-summary">
        <div>
          <span>Overall review</span>
          <strong>
            {counts.RED ?? 0} item{counts.RED === 1 ? "" : "s"}{" "}
            {counts.RED === 1 ? "needs" : "need"} attention
          </strong>
        </div>
        <RiskStat label="Looks standard" value={counts.GREEN ?? 0} tone="green" />
        <RiskStat label="Worth a look" value={counts.YELLOW ?? 0} tone="yellow" />
        <RiskStat label="Needs attention" value={counts.RED ?? 0} tone="red" />
      </div>

      <div className="section-title">
        <div>
          <span className="eyebrow">CLAUSE-BY-CLAUSE REVIEW</span>
          <h3>What this lease means</h3>
        </div>
        <span>Confidence-scored</span>
      </div>

      <ol className="analysis-clauses">
        {document.clauses.map((clause) => (
          <AnalysisClause key={clause.clause_id} clause={clause} />
        ))}
      </ol>

      {document.cross_clause.length > 0 && (
        <section className="connections">
          <span className="eyebrow">CROSS-CLAUSE CONNECTIONS</span>
          <h3>Terms to read together</h3>
          {document.cross_clause.map((connection) => (
            <article key={`${connection.clause_id_a}-${connection.clause_id_b}`}>
              <strong>
                {connection.clause_id_a} ↔ {connection.clause_id_b}
              </strong>
              <span>{connection.relationship_type.replaceAll("_", " ")}</span>
              <p>{connection.explanation}</p>
            </article>
          ))}
        </section>
      )}

      <p className="legal-disclaimer">
        AI-assisted information only — not legal advice. Verify important decisions with a
        qualified professional.
      </p>
    </div>
  );
}

function AnalysisClause({ clause }: { clause: AnalysedClause }) {
  // The model emits GREEN/YELLOW/RED, which means nothing to someone reading their own
  // lease, so the rail shows plain wording and keeps the raw label out of the way.
  const wording: Record<string, string> = {
    GREEN: "Looks standard",
    YELLOW: "Worth a look",
    RED: "Needs attention",
  };

  return (
    <li className={`analysis-clause risk-${clause.risk_label.toLowerCase()}`}>
      <div className="risk-rail">
        <span className="clause-index">{clause.clause_id.replace("c", "")}</span>
        <span className="risk-label">{wording[clause.risk_label] ?? "Not assessed"}</span>
        <small>{Math.round(clause.risk_confidence * 100)}% confidence</small>
      </div>
      <div className="analysis-body">
        {clause.section_heading && <p className="clause-heading-live">{clause.section_heading}</p>}
        <p className="source-clause">{clause.text}</p>
        {clause.error ? (
          // Provider errors carry rate-limit text and an org id. Neither means anything
          // to a reader and the org id should not be on screen, so only the fact that
          // this clause has no explanation is surfaced.
          <p className="notice">
            No plain-language explanation was generated for this clause. The clause text
            above is unaffected.
          </p>
        ) : (
          clause.explanation && (
            <>
              <div className="explanation">
                <span>What this clause says</span>
                <p>{clause.explanation.document_says}</p>
              </div>
              {clause.explanation.concern && (
                <div className="concern">
                  <span>
                    {clause.risk_label === "GREEN" ? "Why it looks fine" : "Why this matters"}
                  </span>
                  <p>{clause.explanation.concern}</p>
                </div>
              )}
              {clause.explanation.statute_support.length > 0 && (
                <div className="statute-list">
                  {clause.explanation.statute_support.map((support) => {
                    // Show the actual provision, not our internal id: the citation and a
                    // link to the official source are what let a reader verify it.
                    const statute = clause.retrieved_statutes.find(
                      (s) => s.entry_id === support.entry_id,
                    );
                    return (
                      <div className="statute" key={support.entry_id}>
                        <strong>The law we checked · {statute?.citation ?? support.entry_id}</strong>
                        <p>{support.how_it_applies}</p>
                        {statute && (
                          <p className="statute-source">
                            <a href={statute.source_url} target="_blank" rel="noreferrer">
                              View the official source
                            </a>{" "}
                            · last checked {statute.last_verified_date}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </>
          )
        )}
        {!clause.explanation && clause.retrieved_statutes.length > 0 && (
          <div className="statute-list">
            {clause.retrieved_statutes.map((statute) => (
              <div className="statute" key={statute.entry_id}>
                <strong>Law that may apply · {statute.citation}</strong>
                <p>“{statute.excerpt_text.length > 320 ? `${statute.excerpt_text.slice(0, 320)}…` : statute.excerpt_text}”</p>
                <p className="statute-source">
                  <a href={statute.source_url} target="_blank" rel="noreferrer">
                    View the official source
                  </a>{" "}
                  · last checked {statute.last_verified_date}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </li>
  );
}

function RiskStat({ label, value, tone }: { label: string; value: number; tone: string }) {
  return (
    <div className={`risk-stat ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Result({
  document,
  onUploadAnother,
}: {
  document: ParsedDocument;
  onUploadAnother: () => void;
}) {
  return (
    <div className="result">
      <div className="result-header">
        <div>
          <span className="eyebrow">CLAUSE BREAKDOWN</span>
          <h2>{document.filename}</h2>
          <p>
            {document.page_count} page{document.page_count === 1 ? "" : "s"} ·{" "}
            {document.extraction_method === "text" ? "embedded text" : document.extraction_method}
          </p>
        </div>
        <button className="secondary-button" onClick={onUploadAnother}>
          Upload another
        </button>
      </div>

      <div className="summary">
        <Stat label="Clauses" value={String(document.clause_count)} />
        <Stat label="Pages" value={String(document.page_count)} />
        <Stat label="Extraction" value={document.extraction_method} />
      </div>

      <div className="section-title">
        <div>
          <span className="eyebrow">EVERY SECTION</span>
          <h3>Clause by clause</h3>
        </div>
        <span>{document.clause_count} total</span>
      </div>

      <ol className="clauses">
        {document.clauses.map((clause) => (
          <li className="clause" key={clause.clause_id}>
            <span className="clause-index">{clause.order + 1}</span>
            <div>
              <div className="clause-meta">
                <strong>{clause.section_heading ?? "Untitled section"}</strong>
                <span>{clause.clause_id}</span>
              </div>
              <p>{clause.text}</p>
            </div>
          </li>
        ))}
      </ol>

      {document.signature_block.length > 0 && (
        <div className="signature-block">
          <span className="eyebrow">SIGNATURE BLOCK</span>
          {document.signature_block.map((line) => (
            <p key={line}>{line}</p>
          ))}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function DocumentReview({
  document,
  onUploadAnother,
}: {
  document: ParsedDocument;
  onUploadAnother: () => void;
}) {
  const [analysed, setAnalysed] = useState<DemoDocument | null>(null);
  const [liveState, setLiveState] = useState<LiveAnalysis | null>(null);
  const [rerun, setRerun] = useState(0);

  return (
    <>
      <LiveAnalysisPanel
        key={rerun}
        document={document}
        forceChoose={rerun > 0 && analysed === null}
        onResult={(result, state) => {
          setAnalysed(result);
          setLiveState(state);
        }}
      />
      {analysed && liveState ? (
        <AnalysisResult
          document={analysed}
          live={{
            explanationsAvailable: liveState.explanations_available,
            onChangeState: () => {
              setAnalysed(null);
              setRerun((n) => n + 1);
            },
          }}
        />
      ) : (
        <Result document={document} onUploadAnother={onUploadAnother} />
      )}
    </>
  );
}
