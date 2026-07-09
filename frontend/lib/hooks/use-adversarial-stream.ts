"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { AdversarialAttempt, BreachCountEvent } from "@/lib/types/adversarial";

const MAX_ATTEMPTS = 100;

export function useAdversarialStream() {
  const [attempts,      setAttempts]      = useState<AdversarialAttempt[]>([]);
  const [breachCount,   setBreachCount]   = useState(0);
  const [lastBreachAt,  setLastBreachAt]  = useState<string | null>(null);
  const [connected,     setConnected]     = useState(false);
  const [backendDown,   setBackendDown]   = useState(false);
  const [totalAttempts, setTotalAttempts] = useState(0);

  const pausedRef = useRef(false);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    const es = new EventSource("/api/sse/adversarial");

    es.addEventListener("open", () => setConnected(true));
    es.addEventListener("error", () => setConnected(false));

    es.addEventListener("backend_down", () => {
      setBackendDown(true);
      setConnected(false);
    });

    es.addEventListener("attempt", (e: MessageEvent) => {
      setBackendDown(false);
      if (pausedRef.current) return;
      try {
        const attempt = JSON.parse(e.data) as AdversarialAttempt;
        setAttempts((prev) => [attempt, ...prev].slice(0, MAX_ATTEMPTS));
        setTotalAttempts((n) => n + 1);
      } catch {
        // ignore malformed events
      }
    });

    es.addEventListener("breach_count", (e: MessageEvent) => {
      try {
        const stats = JSON.parse(e.data) as BreachCountEvent;
        setBreachCount(stats.breach_count);
        setLastBreachAt(stats.last_breach_at);
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
    setAttempts([]);
  }, []);

  return { attempts, breachCount, lastBreachAt, connected, backendDown, paused, togglePause, clear, totalAttempts };
}
