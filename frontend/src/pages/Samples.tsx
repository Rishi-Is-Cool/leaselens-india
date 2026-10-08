import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchAnalysis, listAnalyses, type AnalysisSummary, type DemoDocument } from "../api";
import { AnalysisResult } from "../components/AnalysisView";
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
        <span className="eyebrow">SAMPLE REVIEWS</span>
        <h1>See a finished review</h1>
        <p>
          Synthetic leases written in the formats used across Indian states, reviewed ahead of
          time. No real person's data is involved. The Maharashtra sample shows everything:
          ratings, plain-language explanations, the law it was checked against and clauses to
          read together.
        </p>
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

/** /samples/:slug — one saved review. */
export function SampleReview() {
  const { slug } = useParams();
  const [document, setDocument] = useState<DemoDocument | null>(null);
  const [missing, setMissing] = useState(false);

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
    <div className="page page-narrow">
      <nav className="breadcrumb">
        <Link to="/samples">Sample reviews</Link> <span>/</span> {sampleTitle(document.filename)}
      </nav>
      <AnalysisResult
        document={document}
        title={sampleTitle(document.filename)}
        eyebrow="SAMPLE REVIEW · SYNTHETIC LEASE"
        actions={
          <Link className="primary-button" to="/review">
            Review my own lease
          </Link>
        }
        notices={
          unexplained > 0 ? (
            <p className="notice">
              {unexplained === document.clauses.length
                ? "This sample has risk ratings only; plain-language explanations were not generated for it. The Maharashtra sample shows a complete review."
                : `Plain-language explanations are missing for ${unexplained} of ${document.clauses.length} clauses in this sample.`}
            </p>
          ) : (
            <p className="notice">
              Chat is available on your own uploads: <Link to="/review">upload a lease</Link> to ask
              questions like “When do I get my deposit back?”
            </p>
          )
        }
      />
    </div>
  );
}
