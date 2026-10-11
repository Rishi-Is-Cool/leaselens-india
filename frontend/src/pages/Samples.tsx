import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchAnalysis, listAnalyses, type AnalysisSummary, type DemoDocument } from "../api";
import type { DocumentSource } from "../components/DocumentViewer";
import { Workspace } from "../components/Workspace";
import { sampleSlug, sampleTitle } from "../samples";

function coverage(item: AnalysisSummary): { label: string; tone: string } {
  if (item.explained_count === item.clause_count) return { label: "Fully explained", tone: "good" };
  if (item.explained_count === 0) return { label: "Risk ratings only", tone: "muted" };
  return { label: `${item.explained_count}/${item.clause_count} explained`, tone: "muted" };
}

/** /samples — synthetic leases reviewed in advance, in the real formats of each state. */
export function SamplesIndex() {
  const [items, setItems] = useState<AnalysisSummary[] | null>(null);

  useEffect(() => {
    listAnalyses().then(setItems).catch(() => setItems([]));
  }, []);

  return (
    <div className="page">
      <header className="page-header">
        <h1>Example reviews</h1>
        <p>Made-up agreements in each state's real format. Start with Maharashtra: it shows everything.</p>
      </header>

      {items === null ? (
        <p className="notice">Loading samples…</p>
      ) : (
        <div className="sample-grid">
          {items.map((item) => {
            const badge = coverage(item);
            return (
              <Link key={item.filename} to={`/samples/${sampleSlug(item.filename)}`} className="sample-card">
                <div className="sample-card-top">
                  <span className="state-pill">{item.jurisdiction ?? "No state law check"}</span>
                  <span className={`badge badge-${badge.tone}`}>{badge.label}</span>
                </div>
                <h2>{sampleTitle(item.filename)}</h2>
                <p>
                  {item.clause_count} clauses
                  {item.connection_count > 0 ? ` · ${item.connection_count} linked pairs` : ""}
                </p>
                <span className="card-link">Open review →</span>
              </Link>
            );
          })}
        </div>
      )}

      <section className="cta-band">
        <div>
          <h2>Have your own agreement?</h2>
          <p>Upload it for the same review, then ask questions about it.</p>
        </div>
        <Link className="primary-button" to="/review">
          Review my lease
        </Link>
      </section>
    </div>
  );
}

/** /samples/:slug — one saved review, on its PDF. */
export function SampleReview() {
  const { slug } = useParams();
  const [document, setDocument] = useState<DemoDocument | null>(null);
  const [missing, setMissing] = useState(false);
  const [pdfFailed, setPdfFailed] = useState(false);

  useEffect(() => {
    setDocument(null);
    setMissing(false);
    listAnalyses()
      .then((items) => {
        const match = items.find((i) => sampleSlug(i.filename) === slug);
        if (!match) throw new Error("not found");
        return fetchAnalysis(match.filename);
      })
      .then(setDocument)
      .catch(() => setMissing(true));
  }, [slug]);

  const source = useMemo<DocumentSource | null>(
    () => (document?.pdf && !pdfFailed ? { kind: "pdf", data: document.pdf } : null),
    [document, pdfFailed],
  );

  if (missing)
    return (
      <div className="page page-narrow">
        <section className="card server-notice">
          <h2>Sample not found</h2>
          <Link className="secondary-button" to="/samples">
            All samples
          </Link>
        </section>
      </div>
    );
  if (!document)
    return (
      <div className="page page-narrow">
        <p className="notice">Loading the review…</p>
      </div>
    );

  const unexplained = document.clauses.filter((c) => !c.explanation).length;

  return (
    <Workspace
      header={
        <>
          <div className="ws-title">
            <nav className="breadcrumb">
              <Link to="/samples">Samples</Link> <span>/</span>
            </nav>
            <h1>{sampleTitle(document.filename)}</h1>
            <p>
              Synthetic sample ·{" "}
              {document.jurisdiction ? `checked against ${document.jurisdiction} law` : "no state law check"}
            </p>
          </div>
          <div className="ws-actions">
            <Link className="primary-button" to="/review">
              Check my agreement
            </Link>
          </div>
        </>
      }
      source={source}
      highlights={document.highlights ?? {}}
      textClauses={document.clauses}
      review={document.clauses}
      connections={document.cross_clause}
      onSourceUnavailable={() => setPdfFailed(true)}
      findingsNotice={
        unexplained === document.clauses.length ? (
          <p className="notice">
            This sample has ratings only. The <Link to="/samples/maharashtra-leave-license-mumbai">Maharashtra sample</Link>{" "}
            shows full explanations.
          </p>
        ) : (
          <p className="notice">
            On your own agreement you can also <strong>ask questions</strong>. <Link to="/review">Upload one</Link>.
          </p>
        )
      }
    />
  );
}
