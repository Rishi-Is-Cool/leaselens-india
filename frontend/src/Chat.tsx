import { useEffect, useRef, useState } from "react";
import { ApiError, askAboutLease, type ChatAction, type ChatReply, type ChatTurn } from "./api";
import { Markdown } from "./components/Markdown";

export type QuickAsk = { action: ChatAction; clauseId: string; nonce: number };

export const ACTION_LABELS: Record<ChatAction, string> = {
  explain_simply: "Explain simply",
  why_flagged: "Why this rating?",
  what_to_check: "What should I check?",
};

const SUGGESTIONS = [
  "When do I get my security deposit back?",
  "Can the rent be increased during the term?",
  "How much notice do I have to give before moving out?",
  "What happens if I pay the rent late?",
];

type Message =
  | { role: "user"; text: string }
  | { role: "assistant"; reply: ChatReply }
  | { role: "error"; text: string };

/**
 * Questions about one uploaded lease, answered from its own clauses and its state's
 * statutes. The server refuses verdicts ("is this legal?") and other states' law; this
 * panel renders what it returns, with the clauses and laws each answer relied on.
 *
 * On wide screens it is docked beside the review; on narrow ones a button opens it as a
 * full-screen sheet.
 */
export function ChatPanel({
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
  const [slow, setSlow] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // The free AI tier has a per-minute token allowance; when it is used up an answer waits
  // for the next minute, so say so instead of leaving a spinner unexplained.
  useEffect(() => {
    if (!busy) {
      setSlow(false);
      return;
    }
    const timer = window.setTimeout(() => setSlow(true), 8000);
    return () => window.clearTimeout(timer);
  }, [busy]);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, busy, slow]);

  // A quick action pressed on a clause card arrives here; the nonce makes a repeat press of
  // the same action on the same clause ask again rather than being ignored.
  useEffect(() => {
    if (quickAsk) void send({ action: quickAsk.action, clause_id: quickAsk.clauseId });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [quickAsk?.nonce]);

  // Auto-grow the question box up to a few lines.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  }, [draft]);

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

  return (
    <>
      <button className="chat-launcher" onClick={() => onOpenChange(true)} aria-hidden={open}>
        <span className="chat-launcher-icon" aria-hidden>
          ✦
        </span>
        Ask about this lease
      </button>

      <aside className={`chat-panel ${open ? "chat-open" : ""}`} aria-label="Ask about this lease">
        <header className="chat-header">
          <span className="assistant-avatar" aria-hidden>
            L
          </span>
          <div>
            <h2>Ask LeaseLens</h2>
            <small>
              Answers only from this lease{jurisdiction ? ` and ${jurisdiction} rental law` : ""}
            </small>
          </div>
          {messages.length > 0 && (
            <button className="text-button" onClick={() => setMessages([])} disabled={busy}>
              New chat
            </button>
          )}
          <button className="icon-button chat-close" aria-label="Close chat" onClick={() => onOpenChange(false)}>
            ×
          </button>
        </header>

        <div className="chat-messages" ref={listRef}>
          {!llmConfigured && (
            <p className="notice">
              Chat needs an AI provider, which isn't set up on this server yet. The risk review
              and matching rental law still work.
            </p>
          )}

          {llmConfigured && messages.length === 0 && (
            <div className="chat-empty">
              <span className="assistant-avatar large" aria-hidden>
                L
              </span>
              <h3>What would you like to know?</h3>
              <p>Ask in your own words, or use the buttons under any clause.</p>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="suggestion" onClick={() => void send({ question: s })}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message, index) =>
            message.role === "user" ? (
              <div key={index} className="msg msg-user">
                <div className="msg-bubble">{message.text}</div>
              </div>
            ) : message.role === "error" ? (
              <div key={index} className="msg msg-assistant">
                <span className="assistant-avatar" aria-hidden>
                  L
                </span>
                <div className="msg-body msg-error">{message.text}</div>
              </div>
            ) : (
              <Answer key={index} reply={message.reply} />
            ),
          )}

          {busy && (
            <div className="msg msg-assistant">
              <span className="assistant-avatar" aria-hidden>
                L
              </span>
              <div className="msg-body typing">
                <span className="dots" aria-hidden>
                  <i />
                  <i />
                  <i />
                </span>
                {slow
                  ? "Still working — the free AI tier is busy, so this can take up to a minute."
                  : "Reading your lease…"}
              </div>
            </div>
          )}
        </div>

        <form className="chat-input" onSubmit={submit}>
          <textarea
            ref={inputRef}
            value={draft}
            maxLength={1000}
            rows={1}
            disabled={!llmConfigured}
            placeholder={llmConfigured ? "Ask anything about this lease…" : "Chat is unavailable"}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
          />
          <button
            className="send-button"
            aria-label="Send question"
            disabled={busy || !draft.trim() || !llmConfigured}
          >
            ↑
          </button>
        </form>
        <p className="chat-disclaimer">AI-assisted information, not legal advice. Check important points with a lawyer.</p>
      </aside>
    </>
  );
}

function Answer({ reply }: { reply: ChatReply }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(reply.answer.replaceAll("**", ""));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard blocked: nothing useful to tell the reader.
    }
  }

  return (
    <div className="msg msg-assistant">
      <span className="assistant-avatar" aria-hidden>
        L
      </span>
      <div className={`msg-body ${reply.guarded ? "msg-guarded" : ""}`}>
        {reply.out_of_scope && <span className="chat-tag">Outside this lease</span>}
        <Markdown>{reply.answer}</Markdown>

        {(reply.cited_clauses.length > 0 || reply.cited_statutes.length > 0) && (
          <div className="sources">
            <span className="sources-label">Sources</span>
            <div className="chips">
              {reply.cited_clauses.map((c) => (
                <button key={c.clause_id} className="chip" title={c.snippet} onClick={() => jumpToClause(c.clause_id)}>
                  § Clause {c.clause_id.replace("c", "")}
                  {c.section_heading ? ` · ${c.section_heading}` : ""}
                </button>
              ))}
              {reply.cited_statutes.map((s) => (
                <a key={s.entry_id} className="chip chip-law" href={s.source_url} target="_blank" rel="noreferrer">
                  ⚖ {s.citation} ↗
                </a>
              ))}
            </div>
          </div>
        )}

        <div className="msg-actions">
          <button className="text-button" onClick={() => void copy()}>
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>
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
