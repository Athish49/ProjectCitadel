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
  durationMs: number | null;
  events: TraceEvent[];
}

interface VerdictPayload {
  traceId: string;
  outcome: "BLOCKED" | "HELD" | "CLEAN" | "ERROR";
  blockedByPattern: string | null;
  blockedByLayer: string | null;
  policyHeld: string | null;
  summary: string;
  // Authoritative final state for all 7 layers — always present, always
  // covers every layer (see backend/app/showcase/playground_sse.py). The
  // verdict handler below replaces the client's accumulated layer state with
  // this wholesale, rather than trusting what layer_result events implied.
  layers: LayerResultPayload[];
  ts: string;
}

function isKnownLayerStatus(status: unknown): status is TraceLayerStatus {
  return (
    status === "pending" ||
    status === "running" ||
    status === "passed" ||
    status === "blocked" ||
    status === "held" ||
    status === "skipped" ||
    status === "error" ||
    status === "not_reached"
  );
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
      targetFlow: TargetFlow,
      _sessionMode: SessionMode,
      templateAttack?: { id: number; name: string },
      options?: { isReplay?: boolean; chatSessionId?: string; personaKey?: string; hasAttachment?: boolean }
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
          headers: {
            "Content-Type": "application/json",
            "X-Playground-Token": process.env.NEXT_PUBLIC_PLAYGROUND_TOKEN ?? "",
          },
          body:    JSON.stringify({
            payload,
            tab,
            targetFlow,
            chat_session_id: options?.chatSessionId ?? null,
            persona_key:     options?.personaKey ?? "mark",
            has_attachment:  options?.hasAttachment ?? false,
            ...(templateAttack ? { attackId: templateAttack.id, attackName: templateAttack.name } : {}),
          }),
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
        targetFlow,
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

      // Shared by stream_error and onerror: the stream died before a verdict
      // arrived. Whichever layer was mid-flight becomes "error", everything
      // after it "not_reached" — never left silently "pending"/"running",
      // which would otherwise render as an ambiguous or stale PASS-looking state.
      const markIncomplete = (layers: TraceLayer[]): TraceLayer[] => {
        let sawIncomplete = false;
        return layers.map((l): TraceLayer => {
          // Preserve every real terminal status already reported by the
          // backend (passed/blocked/held/error/skipped) — only "pending" and
          // "running" (client-only placeholders) get rewritten. Rewriting
          // only the first running layer to "error" and leaving the rest
          // "not_reached" would put a PASS row above and a NOT REACHED row
          // directly below a layer the stream actually died inside — the
          // exact ordering inconsistency this fix exists to prevent.
          if (l.status !== "pending" && l.status !== "running") {
            return l;
          }
          const status: TraceLayerStatus = !sawIncomplete && l.status === "running" ? "error" : "not_reached";
          sawIncomplete = true;
          return { ...l, status };
        });
      };

      es.addEventListener("stream_error", (e: MessageEvent) => {
        let message = "Stream error.";
        try {
          message = (JSON.parse(e.data) as { message: string }).message;
        } catch {
          /* malformed payload — keep the generic message */
        }
        setState((prev) => ({
          ...prev,
          isStreaming: false,
          error: message,
          trace: prev.trace ? { ...prev.trace, layers: markIncomplete(prev.trace.layers) } : prev.trace,
        }));
        es.close();
        esRef.current = null;
      });

      es.addEventListener("layer_result", (e: MessageEvent) => {
        let data: LayerResultPayload;
        try {
          data = JSON.parse(e.data) as LayerResultPayload;
        } catch {
          return;
        }
        const idx = layerIndexById(data.layerId);
        if (idx === -1) return;
        const status: TraceLayerStatus = isKnownLayerStatus(data.status) ? data.status : "error";

        setState((prev) => {
          if (!prev.trace) return prev;

          const layers = prev.trace.layers.map((l, i): TraceLayer => {
            if (l.id === data.layerId) {
              return {
                ...l,
                status,
                durationMs: data.durationMs,
                events:     data.events,
              };
            }
            // Mark next layer as running only if this layer passed (not blocked/held/error)
            if (i === idx + 1 && l.status === "pending" && status === "passed") {
              return { ...l, status: "running" };
            }
            return l;
          });

          return { ...prev, trace: { ...prev.trace, layers } };
        });
      });

      es.addEventListener("verdict", (e: MessageEvent) => {
        let data: VerdictPayload;
        try {
          data = JSON.parse(e.data) as VerdictPayload;
        } catch {
          setState((prev) => ({ ...prev, isStreaming: false, error: "Malformed verdict from server." }));
          es.close();
          esRef.current = null;
          return;
        }

        const outcome: TraceVerdict["outcome"] =
          data.outcome === "BLOCKED" || data.outcome === "HELD" || data.outcome === "CLEAN" || data.outcome === "ERROR"
            ? data.outcome
            : "ERROR";
        const verdict: TraceVerdict = {
          outcome,
          blockedByPattern: data.blockedByPattern,
          blockedByLayer:   data.blockedByLayer,
          policyHeld:       data.policyHeld ?? null,
          summary:          data.summary,
        };

        setState((prev) => {
          if (!prev.trace) return { ...prev, isStreaming: false };
          // Authoritative replace: trust verdict.layers over whatever the
          // streamed layer_result events implied, so a layer downstream of
          // the decisive one can never be left (or shown) as PASS. If the
          // payload is malformed (missing/non-array layers), fall back to
          // marking whatever is still pending/running as incomplete rather
          // than throwing inside the state updater.
          let layers: TraceLayer[];
          if (Array.isArray(data.layers)) {
            const byId = new Map(data.layers.map((l) => [l.layerId, l]));
            layers = prev.trace.layers.map((l): TraceLayer => {
              const authoritative = byId.get(l.id);
              if (!authoritative) return { ...l, status: "not_reached" };
              return {
                ...l,
                name:       authoritative.name,
                pattern:    authoritative.pattern,
                status:     isKnownLayerStatus(authoritative.status) ? authoritative.status : "error",
                durationMs: authoritative.durationMs,
                events:     Array.isArray(authoritative.events) ? authoritative.events : [],
              };
            });
          } else {
            layers = markIncomplete(prev.trace.layers);
          }
          return {
            ...prev,
            isStreaming: false,
            trace: { ...prev.trace, layers, verdict },
          };
        });

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
          trace:
            prev.trace && !prev.trace.verdict
              ? { ...prev.trace, layers: markIncomplete(prev.trace.layers) }
              : prev.trace,
        }));
        es.close();
        esRef.current = null;
      };
    },
    []
  );

  return { ...state, submit };
}
