"use client";

import { useState, useRef, useCallback } from "react";
import type {
  AttackComposerTab,
  PlaygroundTrace,
  TraceLayer,
  TraceVerdict,
  TraceLayerStatus,
  TraceEvent,
  TargetFlow,
  SessionMode,
} from "@/lib/types/playground";
import { LAYER_DEFINITIONS as LAYERS } from "@/lib/types/playground";

// ── Types matching SSE server events ─────────────────────────────────────────

interface LayerResultPayload {
  layerId: string;
  name: string;
  pattern: string | null;
  status: TraceLayerStatus;
  durationMs: number;
  events: TraceEvent[];
}

interface VerdictPayload {
  traceId: string;
  outcome: "BLOCKED" | "PARTIAL" | "BREACH" | "CLEAN";
  blockedByPattern: string | null;
  blockedByLayer: string | null;
  summary: string;
  ts: string;
}

// ── Initial pending layers ────────────────────────────────────────────────────

function buildInitialLayers(): TraceLayer[] {
  return LAYERS.map((def, i) => ({
    id:         def.id,
    name:       def.name,
    pattern:    def.pattern,
    status:     i === 0 ? "running" : ("pending" as TraceLayerStatus),
    durationMs: null,
    events:     [],
  }));
}

function layerIndexById(id: string): number {
  return LAYERS.findIndex((l) => l.id === id);
}

// ── Hook ─────────────────────────────────────────────────────────────────────

export interface PlaygroundStreamState {
  trace: PlaygroundTrace | null;
  isStreaming: boolean;
  error: string | null;
}

export function usePlaygroundStream() {
  const [state, setState] = useState<PlaygroundStreamState>({
    trace:       null,
    isStreaming: false,
    error:       null,
  });

  const esRef = useRef<EventSource | null>(null);

  const submit = useCallback(
    async (
      payload: string,
      tab: AttackComposerTab,
      _targetFlow: TargetFlow,
      _sessionMode: SessionMode,
      options?: { isReplay?: boolean }
    ) => {
      // Clean up any previous stream
      esRef.current?.close();
      esRef.current = null;

      setState({ trace: null, isStreaming: true, error: null });

      // ── POST to get traceId + sseUrl ──────────────────────────────────────
      let traceId: string;
      let sseUrl: string;
      let attack: { id: number; name: string };

      try {
        const res = await fetch("/api/showcase/playground", {
          method:  "POST",
          headers: { "Content-Type": "application/json" },
          body:    JSON.stringify({ payload, tab }),
        });

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error((body as { error?: string }).error ?? `HTTP ${res.status}`);
        }

        const data = await res.json() as { traceId: string; sseUrl: string; attack: { id: number; name: string } };
        traceId = data.traceId;
        sseUrl  = data.sseUrl;
        attack  = data.attack;
      } catch (err) {
        setState({ trace: null, isStreaming: false, error: String(err) });
        return;
      }

      // ── Initialise trace with all layers pending ──────────────────────────
      const initialTrace: PlaygroundTrace = {
        traceId,
        attackId:    attack.id,
        attackName:  attack.name,
        tab,
        submittedAt: new Date().toISOString().replace("T", " ").replace(/\.\d+Z$/, "Z"),
        layers:      buildInitialLayers(),
        verdict:     null,
        isExample:   false,
        isReplay:    options?.isReplay ?? false,
      };

      setState({ trace: initialTrace, isStreaming: true, error: null });

      // ── Subscribe to SSE ──────────────────────────────────────────────────
      const es = new EventSource(sseUrl);
      esRef.current = es;

      es.addEventListener("layer_result", (e: MessageEvent) => {
        const data = JSON.parse(e.data) as LayerResultPayload;
        const idx  = layerIndexById(data.layerId);

        setState((prev) => {
          if (!prev.trace) return prev;

          const layers = prev.trace.layers.map((l, i): TraceLayer => {
            if (l.id === data.layerId) {
              return {
                ...l,
                status:     data.status,
                durationMs: data.durationMs,
                events:     data.events,
              };
            }
            // Mark next layer as running (only if still pending)
            if (i === idx + 1 && l.status === "pending") {
              return { ...l, status: "running" };
            }
            return l;
          });

          return { ...prev, trace: { ...prev.trace, layers } };
        });
      });

      es.addEventListener("verdict", (e: MessageEvent) => {
        const data = JSON.parse(e.data) as VerdictPayload;

        const verdict: TraceVerdict = {
          outcome:          data.outcome as TraceVerdict["outcome"],
          blockedByPattern: data.blockedByPattern as TraceVerdict["blockedByPattern"],
          blockedByLayer:   data.blockedByLayer,
          summary:          data.summary,
        };

        setState((prev) => ({
          ...prev,
          isStreaming: false,
          trace: prev.trace ? { ...prev.trace, verdict } : null,
        }));

        es.close();
        esRef.current = null;
      });

      es.onerror = () => {
        setState((prev) => ({
          ...prev,
          isStreaming: false,
          error: prev.trace?.verdict
            ? null
            : "Stream disconnected unexpectedly. Try resubmitting.",
        }));
        es.close();
        esRef.current = null;
      };
    },
    []
  );

  return { ...state, submit };
}
