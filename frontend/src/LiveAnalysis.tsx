import { useEffect, useState } from "react";
import {
  fetchLiveAnalysis,
  startLiveAnalysis,
  type DemoDocument,
  type LiveAnalysis as LiveAnalysisState,
  type ParsedDocument,
} from "./api";

const OTHER_STATE = "__other__";
const POLL_MS = 1500;

/**
 * Runs the risk / statute / explanation review on an uploaded lease. The state is inferred
 * from the lease but always confirmed by the reader before anything runs, because the
 * statutes retrieved depend entirely on it and a wrong guess would cite the wrong law.
 */
export function LiveAnalysisPanel({
  document,
  onResult,
  forceChoose = false,
}: {
  document: ParsedDocument;
  onResult: (analysed: DemoDocument | null, live: LiveAnalysisState | null) => void;
  /** Show the state picker even though a finished review exists, to re-run it. */
  forceChoose?: boolean;
}) {
  const [state, setState] = useState<LiveAnalysisState | null>(null);
  const [choice, setChoice] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [restarted, setRestarted] = useState(false);
  const choosing = forceChoose && !restarted;

  useEffect(() => {
    let cancelled = false;
    setState(null);
    setError(null);
    fetchLiveAnalysis(document.id)
      .then((s) => {
        if (cancelled) return;
        setState(s);
        setChoice(s.jurisdiction ?? s.jurisdiction_hint.jurisdiction ?? OTHER_STATE);
      })
      .catch((e: Error) => !cancelled && setError(e.message));
    return () => {
      cancelled = true;
    };
  }, [document.id]);

  // Poll while running; hand the finished result up so the full review replaces this panel.
  useEffect(() => {
    if (!state) return;
    if (state.status === "done" && state.result && !choosing) {
      onResult(
        {
          filename: document.filename,
          jurisdiction: state.jurisdiction,
          clauses: state.result.clauses,
          cross_clause: state.result.cross_clause,
        },
        state,
      );
      return;
    }
    onResult(null, state);
    if (state.status !== "running") return;
    const timer = window.setTimeout(() => {
      fetchLiveAnalysis(document.id).then(setState).catch((e: Error) => setError(e.message));
    }, POLL_MS);
    return () => window.clearTimeout(timer);
    // onResult is a parent setter wrapper; re-running on its identity would loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, document.id, document.filename, choosing]);

  async function start() {
    setStarting(true);
    setError(null);
    try {
      setState(await startLiveAnalysis(document.id, choice === OTHER_STATE ? null : choice));
      setRestarted(true);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setStarting(false);
    }
  }

  if (error) return <p className="notice notice-bad">{error}</p>;
  if (!state) return <p className="notice">Checking this lease…</p>;

  if (state.status === "running") {
    const { done, total } = state.progress;
    const percent = total ? Math.round((done / total) * 100) : 0;
    return (
      <section className="live-panel">
        <span className="eyebrow">CHECKING YOUR AGREEMENT</span>
        <h3>{done === 0 ? "Getting ready…" : `Clause ${done} of ${total}`}</h3>
        <div className="progress" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
          <div style={{ width: `${Math.max(percent, 4)}%` }} />
        </div>
        <p className="muted-small">
          {state.explanations_available
            ? "Rating each clause, checking the law and writing plain explanations. This takes a minute or two."
            : "This usually takes a few seconds."}
        </p>
      </section>
    );
  }

  if (state.status === "done" && !choosing) return null;

  const hint = state.jurisdiction_hint;
  return (
    <section className="live-panel">
      <span className="eyebrow">ONE QUICK CHECK</span>
      <h3>Which state is this agreement from?</h3>

      <p className="live-hint">
        {hint.jurisdiction ? (
          <>
            It looks like <strong>{hint.jurisdiction}</strong>
            {hint.evidence.length > 0 && <> (it mentions {hint.evidence.slice(0, 3).join(", ")})</>}.
            We'll check it against that state's rent law.
          </>
        ) : hint.unsupported_state ? (
          <>
            It looks like <strong>{hint.unsupported_state}</strong>. We don't cover that state's rent law
            yet, so clauses are rated on their wording alone.
          </>
        ) : hint.ambiguous ? (
          <>It mentions more than one state. Which law applies?</>
        ) : (
          <>We couldn't tell from the document. Please choose.</>
        )}
      </p>

      <label className="state-select">
        <span>State</span>
        <select value={choice} onChange={(e) => setChoice(e.target.value)}>
          {state.supported_jurisdictions.map((j) => (
            <option key={j} value={j}>
              {j}
            </option>
          ))}
          <option value={OTHER_STATE}>Another state (no law check)</option>
        </select>
      </label>

      {!state.llm_configured && (
        <p className="muted-small">
          Explanations need an AI provider, which isn't set up here. You'll still get a rating
          for every clause and the matching law.
        </p>
      )}

      {state.status === "failed" && state.error && <p className="notice notice-bad">{state.error}</p>}

      <button className="primary-button" onClick={start} disabled={starting}>
        {starting
          ? "Starting…"
          : state.status === "failed"
            ? "Try again"
            : choosing
              ? "Check again"
              : "Check this agreement"}
      </button>
    </section>
  );
}
