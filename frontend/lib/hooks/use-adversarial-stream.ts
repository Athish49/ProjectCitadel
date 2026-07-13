"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type {
  AdversarialAttempt,
  AgentStatusValue,
  AgentStatusEvent,
  BreachStatsEvent,
} from "@/lib/types/adversarial";

const MAX_ATTEMPTS = 100;

export function useAdversarialStream() {
  const [attempts,       setAttempts]       = useState<AdversarialAttempt[]>([]);
  const [breachCount,    setBreachCount]     = useState(0);
  const [lastBreachAt,   setLastBreachAt]    = useState<string | null>(null);
  const [totalAttempts,  setTotalAttempts]   = useState(0);
  const [connected,      setConnected]       = useState(false);
  const [backendDown,    setBackendDown]     = useState(false);
  const [agentStatus,    setAgentStatus]     = useState<AgentStatusValue>("CONNECTING");
  const [lastSeenAt,     setLastSeenAt]      = useState<string | null>(null);

  const pausedRef = useRef(false);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    const es = new EventSource("/api/sse/adversarial");

    es.addEventListener("open", () => {
      setConnected(true);
      setBackendDown(false);
    });

    es.addEventListener("error", () => setConnected(false));

    es.addEventListener("backend_down", () => {
      setBackendDown(true);
      setConnected(false);
      setAgentStatus("OFFLINE");
    });

    // Initial history batch from DB — newest-first from backend
    es.addEventListener("history", (e: MessageEvent) => {
      try {
        const history = JSON.parse(e.data) as AdversarialAttempt[];
        if (!pausedRef.current) {
          setAttempts(history.slice(0, MAX_ATTEMPTS));
        }
      } catch {
        // ignore malformed events
      }
    });

    // All-time stats sourced from DB
    es.addEventListener("breach_stats", (e: MessageEvent) => {
      try {
        const stats = JSON.parse(e.data) as BreachStatsEvent;
        setBreachCount(stats.breach_count);
        setLastBreachAt(stats.last_breach_at);
        setTotalAttempts(stats.total_attempts);
      } catch {
        // ignore malformed events
      }
    });

    // Agent liveness derived from DB row recency
    es.addEventListener("agent_status", (e: MessageEvent) => {
      try {
        const status = JSON.parse(e.data) as AgentStatusEvent;
        setAgentStatus(status.status);
        setLastSeenAt(status.last_seen_at);
      } catch {
        // ignore malformed events
      }
    });

    // New live rows from DB polling
    es.addEventListener("attempt", (e: MessageEvent) => {
      if (pausedRef.current) return;
      try {
        const attempt = JSON.parse(e.data) as AdversarialAttempt;
        setAttempts((prev) => [attempt, ...prev].slice(0, MAX_ATTEMPTS));
        setTotalAttempts((n) => n + 1);
        if (attempt.pipeline_verdict === "BREACH") {
          setBreachCount((n) => n + 1);
          setLastBreachAt(attempt.timestamp);
        }
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

  const clear = useCallback(() => setAttempts([]), []);

  return {
    attempts,
    breachCount,
    lastBreachAt,
    totalAttempts,
    connected,
    backendDown,
    paused,
    agentStatus,
    lastSeenAt,
    togglePause,
    clear,
  };
}
