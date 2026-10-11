import { useEffect, useRef, useState } from "react";
import { ACTION_LABELS } from "../Chat";
import type { AnalysedClause, ChatAction, CrossClause } from "../api";
import { RISK_WORDING } from "../samples";

const ORDER = { RED: 0, YELLOW: 1, GREEN: 2 } as const;

/** Short, readable name for a clause: its own heading, else its opening words. A section
 *  heading shared by several clauses ("TERMS AND CONDITIONS") names none of them. */
export function clauseName(clause: AnalysedClause, sharedHeadings: Set<string> = new Set()): string {
  if (clause.section_heading && !sharedHeadings.has(clause.section_heading)) {
    const heading = clause.section_heading.toLowerCase();
    return heading[0].toUpperCase() + heading.slice(1);
  }
  const words = clause.text.split(/\s+/).slice(0, 7).join(" ");
  return `${words}…`;
}

/**
 * The review as a short list: what to question first, then what is worth a look, with
 * standard clauses folded away. Each finding opens to its explanation and the law; the
 * same finding is selected when its highlight is clicked in the document.
 */
export function Findings({
  clauses,
  connections,
  selected,
  onSelect,
  onAsk,
  notice,
}: {
  clauses: AnalysedClause[];
  connections: CrossClause[];
  selected: string | null;
  onSelect: (clauseId: string) => void;
  onAsk?: (action: ChatAction, clauseId: string) => void;
  notice?: React.ReactNode;
}) {
  const sorted = [...clauses].sort(
    (a, b) => ORDER[a.risk_label] - ORDER[b.risk_label] || a.clause_id.localeCompare(b.clause_id),
  );
  const issues = sorted.filter((c) => c.risk_label !== "GREEN");
  const standard = sorted.filter((c) => c.risk_label === "GREEN");
  const red = issues.filter((c) => c.risk_label === "RED").length;
  const yellow = issues.length - red;
  const [showStandard, setShowStandard] = useState(false);
  const headingCounts = new Map<string, number>();
  for (const c of clauses) {
    if (c.section_heading) headingCounts.set(c.section_heading, (headingCounts.get(c.section_heading) ?? 0) + 1);
  }
  const shared = new Set([...headingCounts].filter(([, n]) => n > 1).map(([h]) => h));

  // A standard clause picked in the document must be visible in the list.
  useEffect(() => {
    if (selected && standard.some((c) => c.clause_id === selected)) setShowStandard(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  return (
    <div className="findings">
      <div className="findings-summary">
        <strong>
          {issues.length === 0
            ? "Nothing stood out"
            : [red && `${red} to question`, yellow && `${yellow} worth a look`].filter(Boolean).join(" · ")}
        </strong>
        <span>
          {standard.length} of {clauses.length} clauses look standard
        </span>
      </div>
      {notice}

      <div className="finding-list">
        {issues.map((clause) => (
          <FindingCard
            key={clause.clause_id}
            clause={clause}
            name={clauseName(clause, shared)}
            connections={connections}
            open={selected === clause.clause_id}
            onToggle={() => onSelect(clause.clause_id)}
            onAsk={onAsk}
          />
        ))}
      </div>

      {standard.length > 0 && (
        <div className="standard-group">
          <button className="standard-toggle" onClick={() => setShowStandard((v) => !v)} aria-expanded={showStandard}>
            <span className="risk-dot green" />
            Standard clauses <span className="count">{standard.length}</span>
            <span className="chevron">{showStandard ? "−" : "+"}</span>
          </button>
          {showStandard && (
            <div className="finding-list">
              {standard.map((clause) => (
                <FindingCard
                  key={clause.clause_id}
                  clause={clause}
                  name={clauseName(clause, shared)}
                  connections={connections}
                  open={selected === clause.clause_id}
                  onToggle={() => onSelect(clause.clause_id)}
                  onAsk={onAsk}
                />
              ))}
            </div>
          )}
        </div>
      )}

      <p className="findings-disclaimer">Ratings flag clauses to read carefully. AI-assisted, not legal advice.</p>
    </div>
  );
}

function FindingCard({
  clause,
  name,
  connections,
  open,
  onToggle,
  onAsk,
}: {
  clause: AnalysedClause;
  name: string;
  connections: CrossClause[];
  open: boolean;
  onToggle: () => void;
  onAsk?: (action: ChatAction, clauseId: string) => void;
}) {
  const ref = useRef<HTMLElement>(null);
  const risk = clause.risk_label.toLowerCase();
  const explanation = clause.explanation;
  const linked = connections.filter((c) => c.clause_id_a === clause.clause_id || c.clause_id_b === clause.clause_id);

  useEffect(() => {
    if (open) ref.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [open]);

  return (
    <article ref={ref} className={`finding finding-${risk} ${open ? "finding-open" : ""}`}>
      <button className="finding-head" onClick={onToggle} aria-expanded={open}>
        <span className={`risk-dot ${risk}`} />
        <span className="finding-title">
          <strong>{name}</strong>
          <small>
            Clause {clause.clause_id.replace("c", "")} · {RISK_WORDING[clause.risk_label]}
          </small>
        </span>
        <span className="chevron">{open ? "−" : "+"}</span>
      </button>

      {open && (
        <div className="finding-body">
          {explanation ? (
            <>
              <p className="finding-says">{explanation.document_says}</p>
              {explanation.concern && (
                <div className={`finding-why ${clause.risk_label === "GREEN" ? "ok" : ""}`}>
                  <span>{clause.risk_label === "GREEN" ? "Why it looks fine" : "Why it matters"}</span>
                  <p>{explanation.concern}</p>
                </div>
              )}
              {explanation.statute_support.map((support) => {
                const statute = clause.retrieved_statutes.find((s) => s.entry_id === support.entry_id);
                return (
                  <div className="finding-law" key={support.entry_id}>
                    <strong>⚖ {statute?.citation ?? support.entry_id}</strong>
                    <p>{support.how_it_applies}</p>
                    {statute && (
                      <a href={statute.source_url} target="_blank" rel="noreferrer">
                        Official source ↗
                      </a>
                    )}
                  </div>
                );
              })}
            </>
          ) : (
            <>
              <p className="finding-says muted">
                {clause.error
                  ? "No plain-language explanation was generated for this clause."
                  : "This review has the rating only. Ask about the clause for an explanation."}
              </p>
              {clause.retrieved_statutes.map((statute) => (
                <div className="finding-law" key={statute.entry_id}>
                  <strong>⚖ Law that may apply: {statute.citation}</strong>
                  <a href={statute.source_url} target="_blank" rel="noreferrer">
                    Official source ↗
                  </a>
                </div>
              ))}
            </>
          )}

          {linked.map((connection) => {
            const other = connection.clause_id_a === clause.clause_id ? connection.clause_id_b : connection.clause_id_a;
            return (
              <div className="finding-link" key={`${connection.clause_id_a}-${connection.clause_id_b}`}>
                <span>↔ Read with clause {other.replace("c", "")}</span>
                <p>{connection.explanation}</p>
              </div>
            );
          })}

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
      )}
    </article>
  );
}
