import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ChatPanel, type QuickAsk } from "../Chat";
import { LiveAnalysisPanel } from "../LiveAnalysis";
import {
  deleteDocument,
  fetchDocument,
  listDocuments,
  uploadDocument,
  type DemoDocument,
  type LiveAnalysis,
  type ParsedDocument,
} from "../api";
import { AnalysisResult, ClauseBreakdown } from "../components/AnalysisView";
import { useServer } from "../server";

/** /review — upload a lease, or reopen one uploaded from this browser. */
export function ReviewStart() {
  const { state, health } = useServer();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [reading, setReading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<ParsedDocument[]>([]);

  useEffect(() => {
    if (state === "ready") listDocuments().then(setRecent).catch(() => setRecent([]));
  }, [state]);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setReading(file.name);
    setError(null);
    try {
      const parsed = await uploadDocument(file);
      navigate(`/review/${parsed.id}`);
    } catch (e) {
      setError((e as Error).message);
      setReading(null);
    }
  }

  return (
    <div className="page page-narrow">
      <header className="page-header">
        <span className="eyebrow">REVIEW A LEASE</span>
        <h1>Upload your rental agreement</h1>
        <p>
          We split it into clauses, flag the ones worth questioning, check them against your
          state's rental law and explain each one in plain language. Then you can ask questions
          about it.
        </p>
      </header>

      {state !== "ready" ? (
        <ServerNotice />
      ) : (
        <div className="upload-layout">
          <section className="card upload-card">
            <div
              className={`dropzone ${dragging ? "dropzone-active" : ""} ${reading ? "dropzone-busy" : ""}`}
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
              onClick={() => !reading && inputRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && inputRef.current?.click()}
            >
              {reading ? (
                <>
                  <span className="spinner" aria-hidden />
                  <strong>Reading {reading}…</strong>
                  <span>Scanned pages take a little longer.</span>
                </>
              ) : (
                <>
                  <span className="upload-icon">↑</span>
                  <strong>Drop your lease here</strong>
                  <span>
                    or <u>browse files</u>
                  </span>
                  <small>PDF, or a scan or photo (PNG, JPG) · up to 20 MB</small>
                </>
              )}
            </div>
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf,image/png,image/jpeg"
              hidden
              onChange={(e) => void handleFile(e.target.files?.[0])}
            />
            {error && <p className="notice notice-bad">{error}</p>}
            <p className="muted-small">
              No lease handy? <Link to="/samples">Open a sample review</Link> to see what you get.
            </p>
          </section>

          <aside className="upload-side">
            <section className="card">
              <h2 className="card-title">Your privacy</h2>
              <ul className="check-list">
                <li>Deleted automatically after {health?.retention_hours ?? 24} hours, or right away with one click.</li>
                <li>No account. Only this browser can open what you upload.</li>
                <li>
                  Clause text is sent to an AI provider for explanations and answers. Remove names,
                  ID or bank numbers first if you'd rather not share them.
                </li>
              </ul>
            </section>

            {recent.length > 0 && (
              <section className="card">
                <h2 className="card-title">Your recent uploads</h2>
                <div className="document-list">
                  {recent.map((doc) => (
                    <Link key={doc.id} className="document-item" to={`/review/${doc.id}`}>
                      <span className="document-icon">▤</span>
                      <span>
                        <strong>{doc.filename}</strong>
                        <small>
                          {doc.page_count} page{doc.page_count === 1 ? "" : "s"} · {doc.clause_count} clauses
                        </small>
                      </span>
                    </Link>
                  ))}
                </div>
              </section>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}

function ServerNotice() {
  const { state } = useServer();
  return (
    <section className="card server-notice">
      {state === "static" ? (
        <>
          <h2>Uploads aren't available in this demo build</h2>
          <p>This version of the site only shows reviews prepared in advance.</p>
        </>
      ) : state === "offline" ? (
        <>
          <h2>The review server isn't reachable right now</h2>
          <p>Uploads are switched off until it's back. The sample reviews still work.</p>
        </>
      ) : (
        <>
          <span className="spinner" aria-hidden />
          <h2>Waking up the review server…</h2>
          <p>
            It sleeps when nobody has used it for a while and takes a minute or so to start.
            This page will switch on by itself.
          </p>
        </>
      )}
      <Link className="secondary-button" to="/samples">
        Browse sample reviews
      </Link>
    </section>
  );
}

/** /review/:documentId — one uploaded lease: confirm the state, review, then chat. */
export function ReviewDocument() {
  const { documentId = "" } = useParams();
  const { state } = useServer();
  const navigate = useNavigate();
  const [document, setDocument] = useState<ParsedDocument | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (state !== "ready") return;
    setError(null);
    fetchDocument(documentId)
      .then(setDocument)
      .catch((e: Error) => setError(e.message));
  }, [documentId, state]);

  if (state !== "ready")
    return (
      <div className="page page-narrow">
        <ServerNotice />
      </div>
    );
  if (error)
    return (
      <div className="page page-narrow">
        <section className="card server-notice">
          <h2>This lease isn't available</h2>
          <p>
            It may have been deleted (uploads are removed after 24 hours), or it was uploaded from
            a different browser.
          </p>
          <Link className="primary-button" to="/review">
            Upload a lease
          </Link>
        </section>
      </div>
    );
  if (!document)
    return (
      <div className="page page-narrow">
        <p className="notice">Opening your lease…</p>
      </div>
    );

  return <DocumentReview key={document.id} document={document} onDeleted={() => navigate("/review")} />;
}

function DocumentReview({ document, onDeleted }: { document: ParsedDocument; onDeleted: () => void }) {
  const [analysed, setAnalysed] = useState<DemoDocument | null>(null);
  const [liveState, setLiveState] = useState<LiveAnalysis | null>(null);
  const [rerun, setRerun] = useState(0);
  const [chatOpen, setChatOpen] = useState(false);
  const [quickAsk, setQuickAsk] = useState<QuickAsk | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function remove() {
    if (!window.confirm(`Delete “${document.filename}” and its review now? This can't be undone.`)) return;
    try {
      await deleteDocument(document.id);
      onDeleted();
    } catch (error) {
      setDeleteError((error as Error).message);
    }
  }

  const deleteButton = (
    <button className="danger-button" onClick={() => void remove()}>
      Delete now
    </button>
  );

  const reviewed = analysed && liveState;
  const unexplained = analysed ? analysed.clauses.filter((c) => !c.explanation).length : 0;

  return (
    <div className={`page ${reviewed ? "page-with-chat" : "page-narrow"}`}>
      <div className="review-main">
        <nav className="breadcrumb">
          <Link to="/review">Review a lease</Link> <span>/</span> {document.filename}
        </nav>
        <LiveAnalysisPanel
          key={rerun}
          document={document}
          forceChoose={rerun > 0 && analysed === null}
          onResult={(result, state) => {
            setAnalysed(result);
            setLiveState(state);
          }}
        />
        {deleteError && <p className="notice notice-bad">{deleteError}</p>}
        {reviewed ? (
          <AnalysisResult
            document={analysed}
            title={document.filename}
            eyebrow="YOUR LEASE · REVIEW"
            actions={
              <>
                <button
                  className="secondary-button"
                  onClick={() => {
                    setAnalysed(null);
                    setChatOpen(false);
                    setRerun((n) => n + 1);
                  }}
                >
                  Change state &amp; re-run
                </button>
                {deleteButton}
              </>
            }
            notices={
              !liveState.explanations_available ? (
                <p className="notice">
                  Risk levels come from LeaseLens's offline model, which is less accurate than the
                  full AI review. Plain-language explanations need an AI provider, which isn't set up
                  on this server — the matching rental law is still shown where we hold it.
                </p>
              ) : unexplained > 0 ? (
                <p className="notice">
                  Plain-language explanations could not be generated for {unexplained} of{" "}
                  {analysed.clauses.length} clauses (the AI provider may have hit its daily limit).
                </p>
              ) : null
            }
            onAsk={(action, clauseId) => {
              setChatOpen(true);
              setQuickAsk((previous) => ({ action, clauseId, nonce: (previous?.nonce ?? 0) + 1 }));
            }}
          />
        ) : (
          <ClauseBreakdown document={document} actions={deleteButton} />
        )}
      </div>
      {reviewed && (
        <ChatPanel
          documentId={document.id}
          jurisdiction={liveState.jurisdiction}
          llmConfigured={liveState.llm_configured}
          quickAsk={quickAsk}
          open={chatOpen}
          onOpenChange={setChatOpen}
        />
      )}
    </div>
  );
}
