"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { AuditRow } from "@/lib/types/audit";

const MAX_ROWS = 300;

export function useAuditStream() {
  const [rows,        setRows]        = useState<AuditRow[]>([]);
  const [paused,      setPaused]      = useState(false);
  const [connected,   setConnected]   = useState(false);
  const [backendDown, setBackendDown] = useState(false);

  const pausedRef = useRef(false);

  useEffect(() => {
    const es = new EventSource("/api/sse/audit");

    es.addEventListener("open", () => {
      setConnected(true);
      setBackendDown(false);
    });

    es.addEventListener("error", () => setConnected(false));

    es.addEventListener("backend_down", () => {
      setBackendDown(true);
      setConnected(false);
    });

    // Bulk history batch (newest-first, already sorted by backend)
    es.addEventListener("history", (e: MessageEvent) => {
      setBackendDown(false);
      if (pausedRef.current) return;
      try {
        const history = JSON.parse(e.data) as AuditRow[];
        setRows(history.slice(0, MAX_ROWS));
      } catch {
        // ignore malformed events
      }
    });

    // Live individual rows from DB polling — prepend to keep newest at top
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
