import { useEffect, useMemo, useState, type ReactNode } from "react";
import { Chat, type QuickAsk } from "../Chat";
import type { AnalysedClause, ChatAction, CrossClause, Highlights, RiskLabel } from "../api";
import { DocumentViewer, TextDocument, type DocumentSource, type Focus } from "./DocumentViewer";
import { Findings } from "./Findings";

type Tab = "findings" | "ask";
type MobileView = "document" | "panel";

/**
 * The review screen: the lease itself on the left with clauses highlighted where they
 * appear, and on the right a short list of findings and the chat. Picking a highlight
 * opens its finding; picking a finding scrolls to its highlight. On phones the two halves
 * become tabs.
 */
export function Workspace({
  header,
  source,
  highlights,
  textClauses,
  review,
  connections = [],
  pending,
  scanning = false,
  chat,
  findingsNotice,
  textNotice,
  onSourceUnavailable,
}: {
  header: ReactNode;
  /** The original file, when this browser has it; otherwise the text view is shown. */
  source: DocumentSource | null;
  highlights: Highlights;
  textClauses: { clause_id: string; section_heading?: string | null; text: string }[];
  /** Analysed clauses once the review has run. */
  review: AnalysedClause[] | null;
  connections?: CrossClause[];
  /** Shown in the side panel until the review is ready (state picker, progress). */
  pending?: ReactNode;
  scanning?: boolean;
  chat?: { documentId: string; jurisdiction: string | null; llmConfigured: boolean };
  findingsNotice?: ReactNode;
  textNotice?: ReactNode;
  onSourceUnavailable?: () => void;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const [focus, setFocus] = useState<Focus | null>(null);
  const [tab, setTab] = useState<Tab>("findings");
  // Phones open on the panel: the state picker first, then the short findings list, which
  // reads better than a page shrunk to phone width. The document is one tap away.
  const [mobileView, setMobileView] = useState<MobileView>("panel");
  const [quickAsk, setQuickAsk] = useState<QuickAsk | null>(null);

  const risks = useMemo(
    () => Object.fromEntries((review ?? []).map((c) => [c.clause_id, c.risk_label])) as Record<string, RiskLabel>,
    [review],
  );

  // Open on the most important finding, so the first thing seen is what matters most.
  useEffect(() => {
    if (!review || selected) return;
    const first = review.find((c) => c.risk_label === "RED") ?? review.find((c) => c.risk_label === "YELLOW");
    if (first) {
      setSelected(first.clause_id);
      // After the pages have had a moment to draw, bring that clause into view.
      window.setTimeout(() => scrollTo(first.clause_id), 600);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [review]);

  function scrollTo(clauseId: string) {
    setFocus((f) => ({ clauseId, nonce: (f?.nonce ?? 0) + 1 }));
  }

  function selectFromDocument(clauseId: string) {
    if (!review) return;
    setSelected(clauseId);
    setTab("findings");
    setMobileView("panel");
  }

  function selectFromFindings(clauseId: string) {
    const next = selected === clauseId ? null : clauseId;
    setSelected(next);
    if (next) scrollTo(next);
  }

  function ask(action: ChatAction, clauseId: string) {
    setTab("ask");
    setMobileView("panel");
    setQuickAsk((q) => ({ action, clauseId, nonce: (q?.nonce ?? 0) + 1 }));
  }

  function jumpFromChat(clauseId: string) {
    setSelected(clauseId);
    setMobileView("document");
    scrollTo(clauseId);
  }

  function showMobile(view: MobileView, nextTab?: Tab) {
    setMobileView(view);
    if (nextTab) setTab(nextTab);
    // The document was hidden, so scroll to the selection once it is visible again.
    if (view === "document" && selected) window.setTimeout(() => scrollTo(selected), 50);
  }

  const viewer = source ? (
    <DocumentViewer
      source={source}
      highlights={highlights}
      risks={risks}
      selected={selected}
      focus={focus}
      scanning={scanning}
      onSelect={review ? selectFromDocument : undefined}
      onUnavailable={onSourceUnavailable}
    />
  ) : (
    <TextDocument
      clauses={textClauses}
      risks={risks}
      selected={selected}
      focus={focus}
      scanning={scanning}
      onSelect={review ? selectFromDocument : undefined}
      notice={textNotice}
    />
  );

  return (
    <div className="workspace">
      <div className="ws-bar">{header}</div>

      <div className="ws-mobile-tabs" role="tablist">
        <button role="tab" aria-selected={mobileView === "document"} onClick={() => showMobile("document")}>
          Document
        </button>
        <button
          role="tab"
          aria-selected={mobileView === "panel" && (tab === "findings" || !chat)}
          onClick={() => showMobile("panel", "findings")}
        >
          {review ? "Findings" : "Review"}
        </button>
        {chat && review && (
          <button
            role="tab"
            aria-selected={mobileView === "panel" && tab === "ask"}
            onClick={() => showMobile("panel", "ask")}
          >
            Ask
          </button>
        )}
      </div>

      <div className="ws-body" data-view={mobileView}>
        <section className="ws-doc" aria-label="Your document">
          {viewer}
        </section>

        <aside className="ws-panel">
          {!review ? (
            <div className="ws-panel-scroll">{pending}</div>
          ) : (
            <>
              {chat && (
                <div className="ws-tabs" role="tablist">
                  <button role="tab" aria-selected={tab === "findings"} onClick={() => setTab("findings")}>
                    Findings
                  </button>
                  <button role="tab" aria-selected={tab === "ask"} onClick={() => setTab("ask")}>
                    ✦ Ask
                  </button>
                </div>
              )}
              <div className="ws-panel-scroll" hidden={tab !== "findings"}>
                <Findings
                  clauses={review}
                  connections={connections}
                  selected={selected}
                  onSelect={selectFromFindings}
                  onAsk={chat ? ask : undefined}
                  notice={findingsNotice}
                />
              </div>
              {chat && (
                <div className="ws-panel-chat" hidden={tab !== "ask"}>
                  <Chat
                    documentId={chat.documentId}
                    jurisdiction={chat.jurisdiction}
                    llmConfigured={chat.llmConfigured}
                    quickAsk={quickAsk}
                    onJumpToClause={jumpFromChat}
                  />
                </div>
              )}
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
