import { useState, type ReactNode } from "react";
import { ACTION_LABELS } from "../Chat";
import type { AnalysedClause, ChatAction, DemoDocument, ParsedDocument, RiskLabel } from "../api";
import { RISK_WORDING } from "../samples";

type Filter = "ALL" | RiskLabel;

/** A finished review: summary, filterable clause cards, connections, disclaimer. */
export function AnalysisResult({
  document,
  title,
  eyebrow,
  actions,
  notices,
  onAsk,
}: {
  document: DemoDocument;
  title: string;
  eyebrow: string;
  actions?: ReactNode;
  notices?: ReactNode;
  onAsk?: (action: ChatAction, clauseId: string) => void;
}) {
  const [filter, setFilter] = useState<Filter>("ALL");
  const counts = document.clauses.reduce(
    (acc, clause) => ({ ...acc, [clause.risk_label]: (acc[clause.risk_label] ?? 0) + 1 }),
    {} as Record<string, number>,
  );
  const shown = filter === "ALL" ? document.clauses : document.clauses.filter((c) => c.risk_label === filter);
  const red = counts.RED ?? 0;
  const yellow = counts.YELLOW ?? 0;

  return (
    <div className="analysis-result">
      <header className="result-header">
        <div>
          <span className="eyebrow">{eyebrow}</span>
          <h1 className="result-title">{title}</h1>
          <p>
            {document.jurisdiction
              ? `Checked against ${document.jurisdiction} rental law`
              : "No state rental law checked"}{" "}
            · {document.clauses.length} clauses reviewed
          </p>
        </div>
        {actions && <div className="header-actions">{actions}</div>}
      </header>

      {notices}

      <section className="overview">
        <div className="overview-verdict">
          <span>At a glance</span>
          <strong>
            {red === 0 && yellow === 0
              ? "Nothing stood out as unusual"
              : `${red} clause${red === 1 ? "" : "s"} to question, ${yellow} worth a closer look`}
          </strong>
          <p>Ratings flag clauses for you to read carefully. They are not a legal judgement.</p>
        </div>
        <RiskStat label="Needs attention" value={red} tone="red" />
        <RiskStat label="Worth a look" value={yellow} tone="yellow" />
        <RiskStat label="Looks standard" value={counts.GREEN ?? 0} tone="green" />
      </section>

      <div className="section-title">
        <div>
          <span className="eyebrow">CLAUSE BY CLAUSE</span>
          <h2>What this lease means</h2>
        </div>
        <div className="filter-tabs" role="tablist" aria-label="Filter clauses by rating">
          {(["ALL", "RED", "YELLOW", "GREEN"] as Filter[]).map((f) => (
            <button
              key={f}
              role="tab"
              aria-selected={filter === f}
              className={filter === f ? "active" : ""}
              onClick={() => setFilter(f)}
            >
              {f === "ALL" ? "All" : RISK_WORDING[f]}
              <span>{f === "ALL" ? document.clauses.length : (counts[f] ?? 0)}</span>
            </button>
          ))}
        </div>
      </div>

      <ol className="analysis-clauses">
        {shown.map((clause) => (
          <AnalysisClause key={clause.clause_id} clause={clause} onAsk={onAsk} />
        ))}
        {shown.length === 0 && <p className="empty-filter">No clauses with this rating.</p>}
      </ol>

      {document.cross_clause.length > 0 && (
        <section className="connections">
          <span className="eyebrow">READ TOGETHER</span>
          <h2>Clauses that affect each other</h2>
          {document.cross_clause.map((connection) => (
            <article key={`${connection.clause_id_a}-${connection.clause_id_b}`}>
              <div className="connection-head">
                <a href={`#clause-${connection.clause_id_a}`}>Clause {connection.clause_id_a.replace("c", "")}</a>
                <span aria-hidden>↔</span>
                <a href={`#clause-${connection.clause_id_b}`}>Clause {connection.clause_id_b.replace("c", "")}</a>
                <em>{connection.relationship_type.replaceAll("_", " ")}</em>
              </div>
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

function AnalysisClause({
  clause,
  onAsk,
}: {
  clause: AnalysedClause;
  onAsk?: (action: ChatAction, clauseId: string) => void;
}) {
  return (
    <li id={`clause-${clause.clause_id}`} className={`analysis-clause risk-${clause.risk_label.toLowerCase()}`}>
      <div className="risk-rail">
        <span className="clause-index">{clause.clause_id.replace("c", "")}</span>
        <span className="risk-label">{RISK_WORDING[clause.risk_label] ?? "Not assessed"}</span>
        <small>{Math.round(clause.risk_confidence * 100)}% confidence</small>
      </div>
      <div className="analysis-body">
        {clause.section_heading && <p className="clause-heading-live">{clause.section_heading}</p>}
        <p className="source-clause">{clause.text}</p>
        {clause.error ? (
          // Provider errors carry rate-limit text and an account id: only the fact that
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
                <div className={`concern ${clause.risk_label === "GREEN" ? "concern-ok" : ""}`}>
                  <span>{clause.risk_label === "GREEN" ? "Why it looks fine" : "Why this matters"}</span>
                  <p>{clause.explanation.concern}</p>
                </div>
              )}
              {clause.explanation.statute_support.length > 0 && (
                <div className="statute-list">
                  {clause.explanation.statute_support.map((support) => {
                    // The citation and a link to the official source, not our internal id,
                    // are what let a reader verify the provision.
                    const statute = clause.retrieved_statutes.find((s) => s.entry_id === support.entry_id);
                    return (
                      <div className="statute" key={support.entry_id}>
                        <strong>The law we checked · {statute?.citation ?? support.entry_id}</strong>
                        <p>{support.how_it_applies}</p>
                        {statute && <StatuteSource url={statute.source_url} checked={statute.last_verified_date} />}
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
                <p>
                  “{statute.excerpt_text.length > 320 ? `${statute.excerpt_text.slice(0, 320)}…` : statute.excerpt_text}”
                </p>
                <StatuteSource url={statute.source_url} checked={statute.last_verified_date} />
              </div>
            ))}
          </div>
        )}
        {onAsk && (
          <div className="quick-actions">
            {(Object.keys(ACTION_LABELS) as ChatAction[]).map((action) => (
              <button key={action} onClick={() => onAsk(action, clause.clause_id)}>
                {ACTION_LABELS[action]}
              </button>
            ))}
          </div>
        )}
      </div>
    </li>
  );
}

function StatuteSource({ url, checked }: { url: string; checked: string }) {
  return (
    <p className="statute-source">
      <a href={url} target="_blank" rel="noreferrer">
        View the official source ↗
      </a>{" "}
      · last checked {checked}
    </p>
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

/** The parsed clauses of an upload, shown before its review has run. */
export function ClauseBreakdown({ document, actions }: { document: ParsedDocument; actions?: ReactNode }) {
  return (
    <div className="analysis-result">
      <header className="result-header">
        <div>
          <span className="eyebrow">YOUR LEASE · CLAUSES FOUND</span>
          <h1 className="result-title">{document.filename}</h1>
          <p>
            {document.page_count} page{document.page_count === 1 ? "" : "s"} · {document.clause_count} clauses ·{" "}
            {document.extraction_method === "text"
              ? "read from embedded text"
              : document.extraction_method === "ocr"
                ? "read with OCR"
                : "text and OCR"}
          </p>
        </div>
        {actions && <div className="header-actions">{actions}</div>}
      </header>

      <ol className="clauses">
        {document.clauses.map((clause) => (
          <li className="clause" key={clause.clause_id}>
            <span className="clause-index">{clause.order + 1}</span>
            <div>
              {clause.section_heading && <strong className="clause-heading">{clause.section_heading}</strong>}
              <p>{clause.text}</p>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
