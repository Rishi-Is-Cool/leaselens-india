import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { fetchHealth, STATIC_DEMO, type HealthResponse } from "./api";

// A free-tier API sleeps when idle and takes up to a minute or two to wake. Polling starts
// as soon as any page loads, so by the time a visitor reaches the upload page the server is
// usually awake. Saved sample reviews never depend on it.
const HEALTH_RETRY_MS = 6000;
const HEALTH_ATTEMPTS = 25;

export type ServerState = "connecting" | "waking" | "ready" | "offline" | "static";

type Server = { state: ServerState; health: HealthResponse | null };

const ServerContext = createContext<Server>({ state: "connecting", health: null });

export function ServerProvider({ children }: { children: ReactNode }) {
  const [server, setServer] = useState<Server>({
    state: STATIC_DEMO ? "static" : "connecting",
    health: null,
  });

  useEffect(() => {
    if (STATIC_DEMO) return;
    let cancelled = false;
    let timer: number | undefined;
    let attempts = 0;
    const poll = async () => {
      try {
        const health = await fetchHealth();
        if (!cancelled) setServer({ state: health.database.connected ? "ready" : "offline", health });
      } catch {
        if (cancelled) return;
        attempts += 1;
        if (attempts >= HEALTH_ATTEMPTS) {
          setServer({ state: "offline", health: null });
          return;
        }
        setServer({ state: attempts === 1 ? "connecting" : "waking", health: null });
        timer = window.setTimeout(poll, HEALTH_RETRY_MS);
      }
    };
    void poll();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, []);

  return <ServerContext.Provider value={server}>{children}</ServerContext.Provider>;
}

export function useServer(): Server {
  return useContext(ServerContext);
}

export const SERVER_LABELS: Record<ServerState, string> = {
  connecting: "Connecting…",
  waking: "Waking the server…",
  ready: "Live",
  offline: "Server offline",
  static: "Demo build",
};
