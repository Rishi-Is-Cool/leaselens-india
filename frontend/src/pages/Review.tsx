import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
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
import type { DocumentSource } from "../components/DocumentViewer";
import { Workspace } from "../components/Workspace";
import { forgetFile, loadFile, purgeExpiredFiles, saveFile, type StoredFile } from "../fileStore";
import { useServer } from "../server";

const ACCEPT = "application/pdf,image/png,image/jpeg";

/** /review — drop a lease in. Everything else happens on the review screen. */
export function ReviewStart() {
  const { state, health } = useServer();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [reading, setReading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<ParsedDocument[]>([]);

  useEffect(() => {
    void purgeExpiredFiles();
    if (state === "ready") listDocuments().then(setRecent).catch(() => setRecent([]));
  }, [state]);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    setReading(file.name);
    setError(null);
    try {
      const parsed = await uploadDocument(file);
      await saveFile(parsed.id, file);
      navigate(`/review/${parsed.id}`);
    } catch (e) {
      setError((e as Error).message);
      setReading(null);
    }
  }

  return (
    <div className="page page-narrow upload-page">
      <header className="page-header centered">
        <h1>Check your rental agreement</h1>
        <p>We'll highlight the clauses worth questioning, right on your document.</p>
      </header>

      {state !== "ready" ? (
        <ServerNotice />
      ) : (
        <>
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
                <strong>Drop your agreement here</strong>
                <span>
                  or <u>choose a file</u> · PDF, scan or phone photo
                </span>
              </>
            )}
          </div>
          <input ref={inputRef} type="file" accept={ACCEPT} hidden onChange={(e) => void handleFile(e.target.files?.[0])} />
          {error && <p className="notice notice-bad">{error}</p>}

          <p className="privacy-line">
            🔒 Private: no account, only this browser can open it, and it's deleted within{" "}
            {health?.retention_hours ?? 24} hours. <Link to="/how-it-works#privacy">Details</Link>
          </p>

          {recent.length > 0 && (
            <section className="recent">
              <h2>Continue where you left off</h2>
              {recent.map((doc) => (
                <Link key={doc.id} className="recent-item" to={`/review/${doc.id}`}>
                  <span className="document-icon">▤</span>
                  <span>
                    <strong>{doc.filename}</strong>
                    <small>
                      {doc.page_count} page{doc.page_count === 1 ? "" : "s"} · {doc.clause_count} clauses
                    </small>
                  </span>
                  <span className="chevron">→</span>
                </Link>
              ))}
            </section>
          )}

          <p className="muted-small centered">
            No agreement handy? <Link to="/samples">Try a sample</Link>.
          </p>
        </>
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
          <p>Uploads are switched off until it's back. The samples still work.</p>
        </>
      ) : (
        <>
          <span className="spinner" aria-hidden />
          <h2>Waking up the review server…</h2>
          <p>It sleeps when nobody has used it for a while. This takes about a minute and the page will switch on by itself.</p>
        </>
      )}
      <Link className="secondary-button" to="/samples">
        Try a sample meanwhile
      </Link>
    </section>
  );
}

/** /review/:documentId — one uploaded lease, shown with its highlights. */
export function ReviewDocument() {
  const { documentId = "" } = useParams();
  const { state } = useServer();
  const navigate = useNavigate();
  const [document, setDocument] = useState<ParsedDocument | null>(null);
  const [file, setFile] = useState<StoredFile | null | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadFile(documentId).then(setFile);
  }, [documentId]);

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
          <h2>This agreement isn't available</h2>
          <p>
            It may have been deleted (uploads are removed after 24 hours), or it was uploaded from
            a different browser.
          </p>
          <Link className="primary-button" to="/review">
            Upload an agreement
          </Link>
        </section>
      </div>
    );
  if (!document || file === undefined)
    return (
      <div className="page page-narrow">
        <p className="notice">Opening your agreement…</p>
      </div>
    );

  return (
    <DocumentReview
      key={document.id}
      document={document}
      file={file}
      onFile={setFile}
      onDeleted={() => navigate("/review")}
    />
  );
}

function DocumentReview({
  document,
  file,
  onFile,
  onDeleted,
}: {
  document: ParsedDocument;
  file: StoredFile | null;
  onFile: (file: StoredFile | null) => void;
  onDeleted: () => void;
}) {
  const [analysed, setAnalysed] = useState<DemoDocument | null>(null);
  const [live, setLive] = useState<LiveAnalysis | null>(null);
  const [rerun, setRerun] = useState(0);
  const [pickError, setPickError] = useState<string | null>(null);
  const pickRef = useRef<HTMLInputElement>(null);

  const source = useMemo<DocumentSource | null>(
    () => (file ? { kind: file.type === "application/pdf" ? "pdf" : "image", data: file.blob } : null),
    [file],
  );

  async function remove() {
    if (!window.confirm(`Delete “${document.filename}” and its review now? This can't be undone.`)) return;
    try {
      await deleteDocument(document.id);
      await forgetFile(document.id);
      onDeleted();
    } catch (error) {
      window.alert((error as Error).message);
    }
  }

  async function reopen(picked: File | undefined) {
    if (!picked) return;
    // Highlights are positions in that exact file; a different file would be marked wrongly.
    if (picked.name !== document.filename) {
      setPickError(`That's “${picked.name}”. Please choose “${document.filename}”.`);
      return;
    }
    setPickError(null);
    await saveFile(document.id, picked);
    onFile(await loadFile(document.id));
  }

  const hasHighlights = Object.keys(document.highlights ?? {}).length > 0;
  const running = live?.status === "running";
  const unexplained = analysed ? analysed.clauses.filter((c) => !c.explanation).length : 0;

  const header = (
    <>
      <div className="ws-title">
        <nav className="breadcrumb">
          <Link to="/review">Your agreements</Link> <span>/</span>
        </nav>
        <h1>{document.filename}</h1>
        <p>
          {document.page_count} page{document.page_count === 1 ? "" : "s"} · {document.clause_count} clauses
          {analysed && (analysed.jurisdiction ? ` · checked against ${analysed.jurisdiction} law` : " · no state law check")}
        </p>
      </div>
      <div className="ws-actions">
        {analysed && (
          <button
            className="secondary-button"
            onClick={() => {
              setAnalysed(null);
              setRerun((n) => n + 1);
            }}
          >
            Change state
          </button>
        )}
        <button className="danger-button" onClick={() => void remove()}>
          Delete
        </button>
      </div>
    </>
  );

  return (
    <Workspace
      header={header}
      source={hasHighlights ? source : null}
      highlights={document.highlights ?? {}}
      textClauses={document.clauses}
      review={analysed?.clauses ?? null}
      connections={analysed?.cross_clause ?? []}
      scanning={running}
      onSourceUnavailable={() => onFile(null)}
      chat={
        analysed && live
          ? { documentId: document.id, jurisdiction: live.jurisdiction, llmConfigured: live.llm_configured }
          : undefined
      }
      pending={
        <LiveAnalysisPanel
          key={rerun}
          document={document}
          forceChoose={rerun > 0 && analysed === null}
          onResult={(result, state) => {
            setAnalysed(result);
            setLive(state);
          }}
        />
      }
      findingsNotice={
        live && !live.explanations_available ? (
          <p className="notice">
            Ratings come from the offline model; plain-language explanations need an AI provider,
            which isn't set up on this server.
          </p>
        ) : unexplained > 0 ? (
          <p className="notice">
            Explanations are missing for {unexplained} of {analysed!.clauses.length} clauses (the AI
            provider may have hit its daily limit).
          </p>
        ) : null
      }
      textNotice={
        hasHighlights ? (
          <div className="doc-reopen">
            <span>
              Showing the text. To see the highlights on your original file, choose it again from this
              device. It stays on your device.
            </span>
            <button className="secondary-button" onClick={() => pickRef.current?.click()}>
              Choose {document.filename}
            </button>
            <input ref={pickRef} type="file" accept={ACCEPT} hidden onChange={(e) => void reopen(e.target.files?.[0])} />
            {pickError && <p className="notice notice-bad">{pickError}</p>}
          </div>
        ) : null
      }
    />
  );
}
