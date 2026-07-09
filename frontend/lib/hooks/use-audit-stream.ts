"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { AuditRow } from "@/lib/types/audit";

const MAX_ROWS = 150;

export function useAuditStream() {
  const [rows,        setRows]        = useState<AuditRow[]>([]);
  const [paused,      setPaused]      = useState(false);
  const [connected,   setConnected]   = useState(false);
  const [backendDown, setBackendDown] = useState(false);

  const pausedRef = useRef(false);

  useEffect(() => {
    const es = new EventSource("/api/sse/audit");

    es.addEventListener("open", () => setConnected(true));
    es.addEventListener("error", () => setConnected(false));

    es.addEventListener("backend_down", () => {
      setBackendDown(true);
      setConnected(false);
    });

    es.addEventListener("audit_row", (e: MessageEvent) => {
      setBackendDown(false);
      if (pausedRef.current) return;
      try {
        const row = JSON.parse(e.data) as AuditRow;
        setRows((prev) => [row, ...prev].slice(0, MAX_ROWS));
      } catch {
        // ignore malformed events
      }
    });

    return () => {
      es.close();
      setConnected(false);
    };
  }, []);

  const togglePause = useCallback(() => {
    pausedRef.current = !pausedRef.current;
    setPaused(pausedRef.current);
  }, []);

  const clear = useCallback(() => {
    setRows([]);
  }, []);

  return { rows, paused, connected, backendDown, togglePause, clear };
}
