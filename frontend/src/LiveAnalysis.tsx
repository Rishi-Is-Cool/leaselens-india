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
        <span className="eyebrow">REVIEWING YOUR LEASE</span>
        <h3>
          {done === 0 ? "Getting ready…" : `Checked ${done} of ${total} clauses`}
        </h3>
        <div className="progress" role="progressbar" aria-valuenow={percent} aria-valuemin={0} aria-valuemax={100}>
          <div style={{ width: `${Math.max(percent, 4)}%` }} />
        </div>
        <p className="muted-small">
          {state.explanations_available
            ? "Writing a plain-language explanation for each clause can take a couple of minutes."
            : "This usually takes a few seconds."}
        </p>
      </section>
    );
  }

  if (state.status === "done" && !choosing) return null;

  const hint = state.jurisdiction_hint;
  return (
    <section className="live-panel">
      <span className="eyebrow">NEXT STEP</span>
      <h3>Review the risks in this lease</h3>

      <p className="live-hint">
        {hint.jurisdiction ? (
          <>
            This lease looks like it is from <strong>{hint.jurisdiction}</strong>
            {hint.evidence.length > 0 && <> (it mentions {hint.evidence.slice(0, 3).join(", ")})</>}.
            Please confirm before we check it against that state's rental law.
          </>
        ) : hint.unsupported_state ? (
          <>
            This lease looks like it is from <strong>{hint.unsupported_state}</strong>. We don't hold
            the rental law for that state yet, so clauses will be assessed on their wording alone.
          </>
        ) : hint.ambiguous ? (
          <>This lease mentions more than one state. Please choose which law applies.</>
        ) : (
          <>We couldn't tell which state this lease is from. Please choose one.</>
        )}
      </p>

      <label className="state-select">
        <span>Which state's law applies?</span>
        <select value={choice} onChange={(e) => setChoice(e.target.value)}>
          {state.supported_jurisdictions.map((j) => (
            <option key={j} value={j}>
              {j}
            </option>
          ))}
          <option value={OTHER_STATE}>Another state (no law check yet)</option>
        </select>
      </label>

      {!state.llm_configured && (
        <p className="muted-small">
          Plain-language explanations need an AI provider, which isn't set up on this server.
          You'll still get a risk level for every clause and the matching rental law, where we
          hold it.
        </p>
      )}

      {state.status === "failed" && state.error && <p className="notice notice-bad">{state.error}</p>}

      <button className="primary-button" onClick={start} disabled={starting}>
        {starting
          ? "Starting…"
          : state.status === "failed"
            ? "Try again"
            : choosing
              ? "Re-run the review"
              : "Analyse this lease"}
      </button>
    </section>
  );
}
