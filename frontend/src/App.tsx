import { useEffect, useState } from "react";
import { fetchHealth, type HealthResponse } from "./api";

type State =
  | { phase: "loading" }
  | { phase: "error"; message: string }
  | { phase: "loaded"; health: HealthResponse };

export default function App() {
  const [state, setState] = useState<State>({ phase: "loading" });

  useEffect(() => {
    fetchHealth()
      .then((health) => setState({ phase: "loaded", health }))
      .catch((err: Error) => setState({ phase: "error", message: err.message }));
  }, []);

  return (
    <main className="shell">
      <h1>LeaseLens</h1>
      <p className="tagline">Lease clause analysis — build skeleton (Phase 0)</p>

      <section className="card">
        <h2>Backend health</h2>
        {state.phase === "loading" && <p>Checking backend…</p>}

        {state.phase === "error" && (
          <p className="bad">
            Could not reach the backend: {state.message}
          </p>
        )}

        {state.phase === "loaded" && (
          <dl>
            <dt>API status</dt>
            <dd className={state.health.status === "ok" ? "good" : "warn"}>
              {state.health.status}
            </dd>

            <dt>Service</dt>
            <dd>
              {state.health.service} ({state.health.environment})
            </dd>

            <dt>Database</dt>
            <dd className={state.health.database.connected ? "good" : "bad"}>
              {state.health.database.connected
                ? `connected — Postgres ${state.health.database.server_version}`
                : `not connected (${state.health.database.error})`}
            </dd>
          </dl>
        )}
      </section>
    </main>
  );
}
