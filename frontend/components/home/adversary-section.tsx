"use client";

import { useAdversarialStream } from "@/lib/hooks/use-adversarial-stream";
import { ATTACK_NAMES } from "@/lib/data/matrix";
import { SectionHeader } from "./section-header";

// Real cost model, matching the Adversary page (components/adversary/adversary-view.tsx):
// $0.006 assumed per attempt, capped at $50/month.
const COST_PER_ATTEMPT = 0.006;
const COST_CAP = 50;

function stamp(iso: string): string {
  try {
    const d = new Date(iso);
    const p = (n: number) => (n < 10 ? "0" + n : "" + n);
    return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  } catch {
    return iso;
  }
}

export function AdversarySection() {
  const { attempts, breachCount, totalAttempts, connected, backendDown } = useAdversarialStream();

  const feedState = backendDown ? "OFFLINE" : !connected ? "CONNECTING" : "STREAMING";
  const feedColor = backendDown ? "var(--alert)" : !connected ? "rgba(255,255,255,0.5)" : "var(--ok)";

  const cost = Math.min(COST_CAP, totalAttempts * COST_PER_ATTEMPT);
  const costPct = ((cost / COST_CAP) * 100).toFixed(1);

  const rows = attempts.slice(0, 6);

  return (
    <section style={{ maxWidth: "1264px", margin: "0 auto", padding: "clamp(88px,10vw,150px) 32px 0" }}>
      <SectionHeader
        eyebrow="05 — Adversarial agent"
        title="An attacker that never stops."
        lead="A sandboxed agent mutates payloads on feedback and streams every attempt, breaches included."
        more={{ label: "Open the adversary console", href: "/adversary" }}
      />

      <div data-rv className="panel" style={{ marginTop: "48px", display: "flex", flexWrap: "wrap" }}>
        {/* live feed */}
        <div style={{ flex: "2 1 460px", minWidth: 0, borderRight: "1px solid rgba(255,255,255,0.08)" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "14px 18px",
              borderBottom: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            <span className="eb" style={{ fontSize: "11px" }}>
              Live feed
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              {feedState === "STREAMING" && <span className="live-dot" />}
              <span className="mono" style={{ fontSize: "11.5px", letterSpacing: "0.1em", color: feedColor }}>
                {feedState}
              </span>
            </span>
          </div>

          <div style={{ overflow: "hidden" }}>
            {rows.length === 0 ? (
              <div className="mono" style={{ padding: "22px 18px", fontSize: "12.5px", color: "rgba(255,255,255,0.58)" }}>
                {backendDown ? "Backend unavailable — no live data" : "Waiting for attack attempts…"}
              </div>
            ) : (
              rows.map((a) => {
                const isBreach = a.is_breach || a.pipeline_verdict === "BREACH";
                const isError = a.verdict === "API_ERROR";
                // Attacker's-view colour rule: red = the attack was detected
                // and stopped (BLOCKED), green = it evaded every layer
                // (BREACH — a successful attack, not flagged), amber = error.
                const label = isBreach ? "BREACH" : isError ? "ERROR" : "BLOCKED";
                const color = isBreach ? "var(--ok)" : isError ? "var(--warn)" : "var(--alert)";
                const name = ATTACK_NAMES[a.attack_id] ?? `Attack #${a.attack_id}`;
                const layer = a.blocked_by_layer
                  ? `blocked at ${a.blocked_by_layer}`
                  : isBreach
                  ? "evaded all 7 layers"
                  : "blocked at ingress";
                return (
                  <div
                    key={a.trace_id}
                    className="mono"
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      alignItems: "center",
                      gap: "4px 18px",
                      padding: "12px 18px",
                      borderBottom: "1px solid rgba(255,255,255,0.06)",
                      fontSize: "12.5px",
                      animation: "citadel-row-in 0.5s ease",
                    }}
                  >
                    <span style={{ color: "rgba(255,255,255,0.55)", width: "66px" }}>{stamp(a.timestamp)}</span>
                    <span style={{ flex: "1 1 200px", color: "rgba(255,255,255,0.92)" }}>
                      #{a.attack_id} {name}
                    </span>
                    <span style={{ flex: "1 1 180px", color: "rgba(255,255,255,0.55)" }}>{layer}</span>
                    <span style={{ letterSpacing: "0.08em", color }}>{label}</span>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* counters */}
        <div style={{ flex: "1 1 280px", minWidth: 0, display: "flex", flexDirection: "column" }}>
          <div style={{ padding: "24px 24px", borderBottom: "1px solid rgba(255,255,255,0.08)", flexGrow: 1 }}>
            <div className="eb" style={{ fontSize: "11px" }}>
              Attempts · all-time
            </div>
            <div
              className="mono"
              style={{ marginTop: "12px", fontSize: "32px", lineHeight: 1, fontWeight: 500, fontVariantNumeric: "tabular-nums" }}
            >
              {backendDown ? "—" : totalAttempts.toLocaleString("en-US")}
            </div>
          </div>
          <div style={{ padding: "24px 24px", borderBottom: "1px solid rgba(255,255,255,0.08)", flexGrow: 1 }}>
            <div className="eb" style={{ fontSize: "11px" }}>
              Successful breaches
            </div>
            <div
              className="mono"
              style={{
                marginTop: "12px",
                fontSize: "32px",
                lineHeight: 1,
                fontWeight: 500,
                color: backendDown ? "rgba(255,255,255,0.3)" : "#F0787C",
              }}
            >
              {backendDown ? "—" : breachCount}
            </div>
          </div>
          <div style={{ padding: "24px 24px", flexGrow: 1 }}>
            <div className="eb" style={{ fontSize: "11px" }}>
              Monthly budget
            </div>
            <div className="mono" style={{ marginTop: "12px", fontSize: "20px", lineHeight: 1, fontWeight: 500 }}>
              {backendDown ? (
                "—"
              ) : (
                <>
                  ${cost.toFixed(2)} <span style={{ color: "rgba(255,255,255,0.55)" }}>/ ${COST_CAP.toFixed(2)}</span>
                </>
              )}
            </div>
            <div style={{ marginTop: "14px", height: "4px", background: "rgba(255,255,255,0.1)" }}>
              <div data-grow style={{ height: "4px", width: backendDown ? "0%" : `${costPct}%`, background: "#f4f4f5" }} />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
