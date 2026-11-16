"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { INVARIANT_NAMES, type InvariantName } from "@/lib/data/formal";

export interface RunCheckResult {
  visited: number;
  violations: string[];
  stages_seen: string[];
  elapsed_ms: number;
  all_hold: boolean;
  invariant_results: Partial<Record<InvariantName, boolean>>;
}

const mono = { fontFamily: "var(--font-geist-mono), ui-monospace, monospace" } as const;

/** Fetches the real BFS model checker result from /api/formal/run-check.
 *  Runs once automatically on mount, and again whenever `run()` is called. */
export function useRunCheck() {
  const [data, setData] = useState<RunCheckResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ranOnce = useRef(false);
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    const timeoutId = setTimeout(() => controller.abort(), 15_000);

    try {
      const res = await fetch("/api/formal/run-check", {
        signal: controller.signal,
        cache: "no-store",
      });
      clearTimeout(timeoutId);

      const body = await res.json().catch(() => null);
      if (!res.ok || !body || "error" in body) {
        throw new Error((body && body.error) || `HTTP ${res.status}`);
      }
      setData(body as RunCheckResult);
    } catch (err) {
      clearTimeout(timeoutId);
      const isAbort = err instanceof Error && err.name === "AbortError";
      setError(isAbort ? "timeout" : "unreachable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (ranOnce.current) return;
    ranOnce.current = true;
    run();
  }, [run]);

  return { data, loading, error, run };
}

function UnavailableNote({ error }: { error: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "4px 0" }}>
      <span
        style={{
          width: "20px", height: "20px", borderRadius: "50%",
          border: "1.5px solid rgba(255,255,255,0.14)",
          display: "inline-flex", alignItems: "center", justifyContent: "center",
          flexShrink: 0,
        }}
      >
        <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: "rgba(255,255,255,0.22)" }} />
      </span>
      <span style={{ ...mono, fontSize: "12.5px", color: "rgba(255,255,255,0.4)", lineHeight: 1.6 }}>
        Backend unavailable — the model checker could not be reached.
        {error === "timeout" ? " Request timed out." : ""}
        {" "}<span style={{ color: "rgba(255,255,255,0.26)" }}>No live result to show.</span>
      </span>
    </div>
  );
}

/** Live-wired "exhaustive search" panel for section 04. Shows the real
 *  visited/violations/elapsed_ms/stages_seen/all_hold returned by the BFS
 *  model checker, with a manual re-run and an initial automatic run. */
export function RunCheckPanel({
  data, loading, error, onRerun,
}: {
  data: RunCheckResult | null;
  loading: boolean;
  error: string | null;
  onRerun: () => void;
}) {
  const passCount = data ? Object.values(data.invariant_results).filter(Boolean).length : null;
  const total = INVARIANT_NAMES.length;

  const resultColor = !data ? "rgba(255,255,255,0.62)" : data.all_hold ? "#3ECF8E" : "#E5484D";
  const resultText = loading && !data
    ? "searching…"
    : !data
    ? "no result yet"
    : data.all_hold
    ? `search complete · 0 violations · ${passCount}/${total} invariants hold`
    : `search complete · ${data.violations.length} violation${data.violations.length === 1 ? "" : "s"} · ${passCount}/${total} invariants hold`;

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "24px" }}>
      <div className="panel" style={{ flex: "1.5 1 520px", minWidth: 0 }}>
        <div className="ph">
          <span className="eb" style={{ fontSize: "11px" }}>Live BFS model checker — formal/check_spec.py</span>
          <button
            className="btn btn-g"
            type="button"
            onClick={onRerun}
            disabled={loading}
            style={{ minHeight: "40px", padding: "0 14px", fontSize: "13.5px", opacity: loading ? 0.6 : 1, cursor: loading ? "not-allowed" : "pointer" }}
          >
            {loading ? "Searching…" : "Re-run verification"}
          </button>
        </div>

        <div style={{ padding: "26px 22px 22px" }}>
          {error ? (
            <UnavailableNote error={error} />
          ) : (
            <>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "10px 40px", alignItems: "baseline" }}>
                <div>
                  <span className="mono" style={{ fontSize: "30px", fontWeight: 500 }}>
                    {data ? data.visited.toLocaleString("en-US") : loading ? "—" : "0"}
                  </span>
                  <span style={{ marginLeft: "10px", fontSize: "13.5px", color: "rgba(255,255,255,0.62)" }}>
                    reachable states visited{data ? ` in ${data.elapsed_ms} ms` : ""}
                  </span>
                </div>
                <div className="mono" style={{ fontSize: "13px", color: resultColor }}>{resultText}</div>
              </div>

              {data && data.violations.length > 0 && (
                <div style={{ marginTop: "18px", display: "flex", flexDirection: "column", gap: "6px" }}>
                  {data.violations.map((v) => (
                    <div
                      key={v}
                      className="mono"
                      style={{ fontSize: "12px", color: "#E5484D", padding: "8px 10px", border: "1px solid rgba(229,72,77,0.4)", borderRadius: "4px" }}
                    >
                      {v}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>

      <div className="panel" style={{ flex: "1 1 340px", minWidth: 0 }}>
        <div className="ph"><span className="eb" style={{ fontSize: "11px" }}>Stages reached this run</span></div>
        <div style={{ padding: "18px 22px 22px" }}>
          {error ? (
            <p style={{ margin: 0, fontSize: "13px", color: "rgba(255,255,255,0.35)" }}>No data — backend unreachable.</p>
          ) : data ? (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
              {data.stages_seen.map((s) => (
                <span
                  key={s}
                  className="mono"
                  style={{
                    fontSize: "11px", padding: "6px 10px",
                    border: "1px solid rgba(62,207,142,0.3)",
                    borderRadius: "4px", color: "#3ECF8E",
                  }}
                >
                  {s}
                </span>
              ))}
            </div>
          ) : (
            <p style={{ margin: 0, fontSize: "13px", color: "rgba(255,255,255,0.55)" }}>Running the checker…</p>
          )}
          <p style={{ margin: "14px 0 0", fontSize: "12.5px", color: "rgba(255,255,255,0.45)", lineHeight: 1.6 }}>
            The live endpoint reports which stages the BFS reached, not a per-stage
            count — the state space is small enough that it is re-enumerated in full
            on every run, typically in well under 100&nbsp;ms.
          </p>
        </div>
      </div>
    </div>
  );
}
