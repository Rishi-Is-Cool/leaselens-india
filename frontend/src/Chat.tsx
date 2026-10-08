import { useEffect, useRef, useState } from "react";
import { ApiError, askAboutLease, type ChatAction, type ChatReply, type ChatTurn } from "./api";

export type QuickAsk = { action: ChatAction; clauseId: string; nonce: number };

export const ACTION_LABELS: Record<ChatAction, string> = {
  explain_simply: "Explain simply",
  why_flagged: "Why this rating?",
  what_to_check: "What should I check?",
};

const SUGGESTIONS = [
  "When do I get my security deposit back?",
  "Can the rent be increased, and by how much?",
  "How much notice do I have to give before moving out?",
];

type Message =
  | { role: "user"; text: string }
  | { role: "assistant"; reply: ChatReply }
  | { role: "error"; text: string };

/**
 * Questions about one uploaded lease, answered from its own clauses and its state's
 * statutes. The server refuses verdicts ("is this legal?") and other states' law; this
 * panel only renders what it returns, with the clauses and laws each answer relied on.
 */
export function ChatDrawer({
  documentId,
  jurisdiction,
  llmConfigured,
  quickAsk,
  open,
  onOpenChange,
}: {
  documentId: string;
  jurisdiction: string | null;
  llmConfigured: boolean;
  quickAsk: QuickAsk | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  // A quick action pressed on a clause card arrives here; the nonce makes a repeat press of
  // the same action on the same clause ask again rather than being ignored.
  useEffect(() => {
    if (quickAsk) void send({ action: quickAsk.action, clause_id: quickAsk.clauseId });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quickAsk?.nonce]);

  function history(): ChatTurn[] {
    return messages.flatMap((m): ChatTurn[] =>
      m.role === "user"
        ? [{ role: "user", content: m.text }]
        : m.role === "assistant"
          ? [{ role: "assistant", content: m.reply.answer }]
          : [],
    );
  }

  async function send(body: { question?: string; action?: ChatAction; clause_id?: string }) {
    if (busy || !llmConfigured) return;
    const shown = body.question ?? `${ACTION_LABELS[body.action!]} — clause ${body.clause_id!.replace("c", "")}`;
    setMessages((m) => [...m, { role: "user", text: shown }]);
    setDraft("");
    setBusy(true);
    try {
      const reply = await askAboutLease(documentId, { ...body, history: history().slice(-6) });
      setMessages((m) => [...m, { role: "assistant", reply }]);
    } catch (error) {
      const text =
        error instanceof ApiError && error.status === 429
          ? "You've asked a lot of questions in a short time. Please try again in a little while."
          : (error as Error).name === "TypeError"
            ? "Couldn't reach the LeaseLens server. Check your connection and try again."
            : (error as Error).message;
      setMessages((m) => [...m, { role: "error", text }]);
    } finally {
      setBusy(false);
    }
  }

  function submit(event?: React.FormEvent) {
    event?.preventDefault();
    const question = draft.trim();
    if (question) void send({ question });
  }

  if (!open) {
    return (
      <button className="chat-launcher" onClick={() => onOpenChange(true)}>
        <span aria-hidden>?</span> Ask about this lease
      </button>
    );
  }

  return (
    <aside className="chat-drawer" aria-label="Ask about this lease">
      <header>
        <div>
          <span className="eyebrow">DOCUMENT-AWARE CHAT</span>
          <h3>Ask about this lease</h3>
          <small>
            Answers come only from this lease
            {jurisdiction ? ` and ${jurisdiction} rental law` : ""}.
          </small>
        </div>
        <button className="icon-button" aria-label="Close chat" onClick={() => onOpenChange(false)}>
          ×
        </button>
      </header>

      <div className="chat-messages" ref={listRef}>
        {!llmConfigured && (
          <p className="notice">
            Chat needs an AI provider, which isn't set up on this server yet. The risk review
            and matching rental law above still work.
          </p>
        )}

        {llmConfigured && messages.length === 0 && (
          <div className="chat-empty">
            <p>Ask in your own words, or use the buttons on any clause. Try:</p>
            {SUGGESTIONS.map((s) => (
              <button key={s} className="suggestion" onClick={() => void send({ question: s })}>
                {s}
              </button>
            ))}
          </div>
        )}

        {messages.map((message, index) =>
          message.role === "user" ? (
            <div key={index} className="bubble bubble-user">
              {message.text}
            </div>
          ) : message.role === "error" ? (
            <div key={index} className="bubble bubble-error">
              {message.text}
            </div>
          ) : (
            <Answer key={index} reply={message.reply} />
          ),
        )}

        {busy && <div className="bubble bubble-assistant typing">Reading your lease…</div>}
      </div>

      <form className="chat-input" onSubmit={submit}>
        <textarea
          value={draft}
          maxLength={1000}
          rows={2}
          disabled={!llmConfigured}
          placeholder={llmConfigured ? "e.g. Can my landlord keep the deposit?" : "Chat is unavailable"}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
        />
        <button className="primary-button" disabled={busy || !draft.trim() || !llmConfigured}>
          Ask
        </button>
      </form>
      <p className="chat-disclaimer">AI-assisted information only — not legal advice.</p>
    </aside>
  );
}

function Answer({ reply }: { reply: ChatReply }) {
  return (
    <div className={`bubble bubble-assistant ${reply.guarded ? "bubble-guarded" : ""}`}>
      {reply.out_of_scope && <span className="chat-tag">Outside this lease</span>}
      <p>{reply.answer}</p>

      {reply.cited_clauses.length > 0 && (
        <div className="chips">
          <span>From your lease:</span>
          {reply.cited_clauses.map((c) => (
            <button
              key={c.clause_id}
              className="chip"
              title={c.snippet}
              onClick={() => jumpToClause(c.clause_id)}
            >
              Clause {c.clause_id.replace("c", "")}
              {c.section_heading ? ` · ${c.section_heading}` : ""}
            </button>
          ))}
        </div>
      )}

      {reply.cited_statutes.length > 0 && (
        <div className="chips">
          <span>Law checked:</span>
          {reply.cited_statutes.map((s) => (
            <a key={s.entry_id} className="chip chip-law" href={s.source_url} target="_blank" rel="noreferrer">
              {s.citation}
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

function jumpToClause(clauseId: string) {
  const element = document.getElementById(`clause-${clauseId}`);
  if (!element) return;
  element.scrollIntoView({ behavior: "smooth", block: "center" });
  element.classList.add("clause-flash");
  window.setTimeout(() => element.classList.remove("clause-flash"), 1600);
}
