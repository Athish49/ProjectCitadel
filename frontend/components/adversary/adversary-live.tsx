"use client";

import { useMemo } from "react";
import { useAdversarialStream } from "@/lib/hooks/use-adversarial-stream";
import { useAuditStream } from "@/lib/hooks/use-audit-stream";
import type { AdversarialAttempt } from "@/lib/types/adversarial";
import type { AuditRow } from "@/lib/types/audit";
import { MATRIX_ROWS, ATTACK_NAMES as ATTACK_NAME } from "@/lib/data/matrix";

const mono: React.CSSProperties = { fontFamily: "var(--font-geist-mono), monospace" };

const COST_PER_ATTEMPT = 0.006;
const MONTHLY_CAP = 50;

function fmtTime(iso: string): string {
  try {
    const d = new Date(iso);
    const p = (n: number) => String(n).padStart(2, "0");
    return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  } catch {
    return iso;
  }
}

function fmtRelative(iso: string | null): string {
  if (!iso) return "never";
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

function AttemptFeedRow({ attempt }: { attempt: AdversarialAttempt }) {
  const isBreach = attempt.verdict === "EVADED_INGRESS";
  const isError  = attempt.verdict === "API_ERROR";
  const outcomeLabel = isBreach ? "BREACH" : isError ? "ERROR" : "BLOCKED";
  const outcomeColor = isBreach ? "#E5484D" : isError ? "#E2A336" : "#3ECF8E";
  const name = ATTACK_NAME[attempt.attack_id] ?? `Attack #${attempt.attack_id}`;
  const layer = attempt.sanitizer_detections[0] ?? (isBreach ? "evaded_ingress" : "ingress_pass");
  const detail = attempt.sanitizer_detections.length > 0
    ? attempt.sanitizer_detections.join(", ")
    : isBreach
    ? "no patterns detected — evaded"
    : "clean pass";

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "4px",
        padding: "12px 18px",
        borderBottom: "1px solid rgba(255,255,255,0.05)",
        animation: "citadel-rowin 0.4s ease forwards",
      }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "68px 1fr 90px",
          gap: "12px",
          alignItems: "baseline",
          ...mono,
          fontSize: "12px",
        }}
      >
        <span style={{ color: "rgba(255,255,255,0.32)" }}>{fmtTime(attempt.timestamp)}</span>
        <span style={{ color: "rgba(255,255,255,0.8)", fontFamily: "var(--font-geist), sans-serif", fontSize: "13px" }}>
          #{attempt.attack_id} {name}
        </span>
        <span style={{ textAlign: "right", color: outcomeColor, fontWeight: 600, letterSpacing: "0.04em" }}>
          {outcomeLabel}
        </span>
      </div>
      <div style={{ fontSize: "11.5px", color: "rgba(255,255,255,0.3)", ...mono, paddingLeft: "1px" }}>
        {isBreach ? "evaded at " : "blocked at "}
        <span style={{ color: "rgba(255,255,255,0.45)" }}>{layer}</span>
        {" · "}
        <span style={{ color: "rgba(255,255,255,0.25)" }}>{detail}</span>
      </div>
    </div>
  );
}

function AuditFeedRow({ row }: { row: AuditRow }) {
  const sevColor = row.severity === "alert" ? "#E5484D"
    : row.severity === "warn" ? "#E2A336"
    : row.severity === "info" ? "#5BB5F2"
    : "#3ECF8E";

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "60px 120px 1fr 80px",
        gap: "10px",
        padding: "8px 18px",
        borderBottom: "1px solid rgba(255,255,255,0.04)",
        ...mono,
        fontSize: "11px",
        animation: "citadel-rowin 0.3s ease forwards",
      }}
    >
      <span style={{ color: "rgba(255,255,255,0.3)" }}>{fmtTime(row.ts)}</span>
      <span style={{ color: "rgba(255,255,255,0.5)" }}>{row.agent}</span>
      <span style={{ color: "rgba(255,255,255,0.65)" }}>
        {row.action}
        {row.label ? <span style={{ color: "rgba(255,255,255,0.3)", marginLeft: "6px" }}>[{row.label}]</span> : null}
      </span>
      <span style={{ textAlign: "right", color: sevColor, letterSpacing: "0.04em" }}>{row.outcome}</span>
    </div>
  );
}

function UnavailableMessage({ label }: { label: string }) {
  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "10px",
        padding: "32px 18px",
      }}
    >
      <div style={{ width: "28px", height: "28px", borderRadius: "50%", border: "1.5px solid rgba(255,255,255,0.12)", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "rgba(255,255,255,0.18)" }} />
      </div>
      <div style={{ ...mono, fontSize: "12px", color: "rgba(255,255,255,0.35)", textAlign: "center", lineHeight: 1.7 }}>
        Backend unavailable
        <br />
        <span style={{ color: "rgba(255,255,255,0.2)", fontSize: "11px" }}>{label} · no data to display</span>
      </div>
    </div>
  );
}

export function AdversaryLive() {
  const {
    attempts,
    breachCount,
    lastBreachAt,
    connected,
    backendDown,
    paused,
    togglePause,
    clear: clearAttempts,
    totalAttempts,
  } = useAdversarialStream();

  const {
    rows: auditRows,
    paused: auditPaused,
    connected: auditConnected,
    backendDown: auditBackendDown,
    togglePause: toggleAuditPause,
    clear: clearAudit,
  } = useAuditStream();

  const advSpend   = Math.min(MONTHLY_CAP, totalAttempts * COST_PER_ATTEMPT);
  const spendPct   = Math.min(100, (advSpend / MONTHLY_CAP) * 100);
  const spendColor = spendPct > 90 ? "#E5484D" : spendPct > 70 ? "#E2A336" : "#3ECF8E";

  const streamColor = paused ? "rgba(255,255,255,0.4)" : "#3ECF8E";

  const agentStatus      = backendDown ? "OFFLINE" : connected ? "LIVE" : "CONNECTING";
  const agentStatusColor = backendDown ? "#E5484D" : connected ? "#3ECF8E" : "rgba(255,255,255,0.4)";

  const focusCatName = useMemo(() => {
    if (attempts.length === 0) return null;
    const latest = attempts[0];
    const row = MATRIX_ROWS.find((r) => r.id === latest.attack_id);
    return row ? `${row.catShort} attacks` : null;
  }, [attempts]);

  const feedUnavailable = backendDown && attempts.length === 0;
  const auditUnavailable = auditBackendDown && auditRows.length === 0;

  return (
    <div>
      {/* Hero stats */}
      <div
        data-hero-stats=""
        style={{
          marginTop: "52px",
          borderTop: "1px solid rgba(255,255,255,0.09)",
          borderBottom: "1px solid rgba(255,255,255,0.09)",
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
        }}
      >
        {/* Attempts */}
        <div
          style={{
            padding: "26px 28px",
            borderRight: "1px solid rgba(255,255,255,0.07)",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
          }}
        >
          <div style={{ ...mono, fontSize: "11px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.4)" }}>
            ATTACKS CAPTURED
          </div>
          <div style={{ ...mono, fontSize: "34px", fontWeight: 600, letterSpacing: "-0.02em", color: "rgba(255,255,255,0.95)" }}>
            {backendDown ? "—" : totalAttempts.toLocaleString("en-US")}
          </div>
          <div style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.38)" }}>
            {backendDown ? "waiting for backend" : "this session"}
          </div>
        </div>

        {/* Successful breaches */}
        <div
          style={{
            padding: "26px 28px",
            borderRight: "1px solid rgba(255,255,255,0.07)",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
          }}
        >
          <div style={{ ...mono, fontSize: "11px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.4)" }}>
            SUCCESSFUL BREACHES
          </div>
          <div style={{ ...mono, fontSize: "34px", fontWeight: 600, letterSpacing: "-0.02em", color: backendDown ? "rgba(255,255,255,0.3)" : "#E5484D" }}>
            {backendDown ? "—" : breachCount}
          </div>
          <div style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.38)" }}>
            {backendDown ? "waiting for backend" : lastBreachAt ? `last: ${fmtRelative(lastBreachAt)}` : "none detected"}
          </div>
        </div>

        {/* Agent status */}
        <div style={{ padding: "26px 28px", display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ ...mono, fontSize: "11px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.4)" }}>
            AGENT STATUS
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", ...mono, fontSize: "26px", fontWeight: 600, letterSpacing: "-0.02em", color: agentStatusColor }}>
            <span
              style={{
                width: "9px",
                height: "9px",
                borderRadius: "50%",
                background: agentStatusColor,
                animation: connected && !backendDown ? "citadel-pulse 2.2s ease-in-out infinite" : "none",
                flexShrink: 0,
              }}
            />
            {agentStatus}
          </div>
          <div style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.38)" }}>
            {backendDown ? "backend not reachable" : focusCatName ? `focused on ${focusCatName}` : "awaiting first attempt"}
          </div>
        </div>
      </div>

      {/* System status bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "12px 2px 0",
          ...mono,
          fontSize: "11.5px",
          color: "rgba(255,255,255,0.32)",
        }}
      >
        <span
          style={{
            width: "6px",
            height: "6px",
            borderRadius: "50%",
            background: backendDown ? "#E5484D" : connected ? "#3ECF8E" : "rgba(255,255,255,0.3)",
            animation: connected && !backendDown ? "citadel-pulse 2.2s ease-in-out infinite" : "none",
            flexShrink: 0,
          }}
        />
        {backendDown
          ? "SYSTEM: BACKEND UNAVAILABLE — /sse/adversarial unreachable · retrying"
          : `SYSTEM: ${connected ? "LIVE" : "CONNECTING"} — telemetry from /sse/adversarial · sandboxed instance only, never the live showcase`}
      </div>

      {/* Feed + sidebar — stretch so feed matches sidebar height */}
      <div
        data-main-grid=""
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 360px",
          gap: "20px",
          alignItems: "stretch",
          marginTop: "64px",
        }}
      >
        {/* Live attack feed — wrapped with section label */}
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ width: "7px", height: "7px", borderRadius: "50%", background: "#E5484D", flexShrink: 0 }} />
              <span style={{ fontSize: "13px", fontWeight: 600, letterSpacing: "0.06em", color: "rgba(255,255,255,0.85)", textTransform: "uppercase" }}>
                Attacker&apos;s View
              </span>
            </div>
            <div style={{ marginTop: "4px", paddingLeft: "15px", fontSize: "12px", color: "rgba(255,255,255,0.35)" }}>
              Every attack attempt the adversarial agent fires — blocked or evaded
            </div>
          </div>
        <div
          style={{
            border: "1px solid rgba(255,255,255,0.09)",
            background: "#0C0D0F",
            display: "flex",
            flexDirection: "column",
            flex: 1,
          }}
        >
          {/* Feed header */}
          <div
            style={{
              padding: "14px 18px",
              borderBottom: "1px solid rgba(255,255,255,0.07)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "12px",
              flexShrink: 0,
            }}
          >
            <span style={{ ...mono, fontSize: "11px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.4)" }}>
              LIVE FEED — /sse/adversarial
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "7px",
                  ...mono,
                  fontSize: "11px",
                  color: feedUnavailable ? "#E5484D" : streamColor,
                }}
              >
                <span
                  style={{
                    width: "6px",
                    height: "6px",
                    borderRadius: "50%",
                    background: feedUnavailable ? "#E5484D" : streamColor,
                    animation: !feedUnavailable && !paused ? "citadel-pulse 2.2s ease-in-out infinite" : "none",
                  }}
                />
                {feedUnavailable ? "UNAVAILABLE" : paused ? "PAUSED" : "STREAMING"}
              </span>
              {!feedUnavailable && (
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    onClick={togglePause}
                    className="btn-outline"
                    style={{ background: "transparent", ...mono, fontSize: "11px", padding: "5px 11px", borderRadius: "5px", cursor: "pointer" }}
                  >
                    {paused ? "Resume" : "Pause"}
                  </button>
                  <button
                    onClick={clearAttempts}
                    className="btn-outline"
                    style={{ background: "transparent", ...mono, fontSize: "11px", padding: "5px 11px", borderRadius: "5px", cursor: "pointer" }}
                  >
                    Clear
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Feed body — fills remaining height */}
          <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column" }}>
            {feedUnavailable ? (
              <UnavailableMessage label="/sse/adversarial" />
            ) : attempts.length === 0 ? (
              <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", ...mono, fontSize: "12px", color: "rgba(255,255,255,0.3)" }}>
                waiting for attack attempts…
              </div>
            ) : (
              attempts.map((a) => <AttemptFeedRow key={a.trace_id} attempt={a} />)
            )}
          </div>
        </div>
        </div>

        {/* Sidebar */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Budget */}
          <div
            style={{
              border: "1px solid rgba(255,255,255,0.09)",
              background: "#0C0D0F",
              padding: "20px 22px",
            }}
          >
            <div style={{ ...mono, fontSize: "11px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.4)" }}>
              MONTHLY COST — CLAUDE HAIKU 4.5
            </div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "8px", marginTop: "12px" }}>
              <span style={{ ...mono, fontSize: "30px", fontWeight: 600, color: backendDown ? "rgba(255,255,255,0.3)" : spendColor }}>
                {backendDown ? "—" : `$${advSpend.toFixed(2)}`}
              </span>
              <span style={{ ...mono, fontSize: "14px", color: "rgba(255,255,255,0.4)" }}>
                / ${MONTHLY_CAP.toFixed(2)} cap
              </span>
            </div>
            <div
              style={{
                marginTop: "14px",
                height: "5px",
                background: "rgba(255,255,255,0.08)",
                overflow: "hidden",
                borderRadius: "3px",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: backendDown ? "0%" : `${spendPct.toFixed(1)}%`,
                  background: spendColor,
                  transition: "width 1s ease",
                }}
              />
            </div>
            <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.42)", marginTop: "12px", lineHeight: 1.55 }}>
              Hard cap enforced by P11 (Token &amp; Cost Budgets). ~$0.006 per attempt. A circuit breaker halts the agent outright on exhaustion — it does not silently degrade.
            </div>
          </div>

          {/* Agent profile */}
          <div
            style={{
              border: "1px solid rgba(255,255,255,0.09)",
              background: "#0C0D0F",
              padding: "20px 22px",
              display: "flex",
              flexDirection: "column",
              gap: "14px",
            }}
          >
            <span style={{ ...mono, fontSize: "11px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.4)" }}>
              AGENT PROFILE
            </span>
            <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "13px" }}>
              {[
                { label: "Model",     value: "Claude Haiku 4.5",                                    mono: true  },
                { label: "Isolation", value: "Separate container, sandboxed test instance only",    mono: false },
                { label: "Reaches",   value: "Adversarial-test API only — never the live showcase", mono: false },
              ].map(({ label, value, mono: isMono }) => (
                <div key={label} style={{ display: "flex", justifyContent: "space-between", gap: "10px" }}>
                  <span style={{ color: "rgba(255,255,255,0.42)", flexShrink: 0 }}>{label}</span>
                  <span
                    style={{
                      color: "rgba(255,255,255,0.85)",
                      textAlign: "right",
                      maxWidth: "190px",
                      ...(isMono ? { ...mono, fontSize: "12.5px" } : {}),
                    }}
                  >
                    {value}
                  </span>
                </div>
              ))}
            </div>
            <div
              style={{
                borderTop: "1px solid rgba(255,255,255,0.07)",
                paddingTop: "12px",
                fontSize: "12.5px",
                lineHeight: 1.6,
                color: "rgba(255,255,255,0.5)",
              }}
            >
              Rotates through the taxonomy category by category; mutates payloads using feedback from blocked vs. partially-leaked outcomes. The strategy is open-source and displayed verbatim — no proprietary technique withheld.
            </div>
            <div style={{ ...mono, fontSize: "11.5px", color: "rgba(255,255,255,0.38)" }}>
              adversarial/strategy.py:1
            </div>
          </div>

          {/* Testing now */}
          <div
            style={{
              border: "1px solid rgba(255,255,255,0.09)",
              background: "#0C0D0F",
              padding: "18px 22px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "12px",
            }}
          >
            <div>
              <div style={{ ...mono, fontSize: "11px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.4)" }}>
                TESTING NOW
              </div>
              <div style={{ fontSize: "15px", fontWeight: 600, color: "rgba(255,255,255,0.92)", marginTop: "6px" }}>
                {backendDown ? "—" : (focusCatName ?? "awaiting data")}
              </div>
            </div>
            <span
              style={{
                width: "8px",
                height: "8px",
                borderRadius: "50%",
                background: agentStatusColor,
                animation: connected && !backendDown ? "citadel-pulse 2.2s ease-in-out infinite" : "none",
                flexShrink: 0,
              }}
            />
          </div>
        </div>
      </div>

      {/* Live Audit Feed */}
      <div style={{ marginTop: "48px" }}>
        <div style={{ marginBottom: "12px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ width: "7px", height: "7px", borderRadius: "50%", background: "#3ECF8E", flexShrink: 0 }} />
            <span style={{ fontSize: "13px", fontWeight: 600, letterSpacing: "0.06em", color: "rgba(255,255,255,0.85)", textTransform: "uppercase" }}>
              Defender&apos;s View
            </span>
          </div>
          <div style={{ marginTop: "4px", paddingLeft: "15px", fontSize: "12px", color: "rgba(255,255,255,0.35)" }}>
            Real-time audit trail — every agent action, tool call, and security event across the pipeline
          </div>
        </div>
        <div
          style={{
            border: "1px solid rgba(255,255,255,0.09)",
            background: "#0C0D0F",
          }}
        >
          {/* Audit header */}
          <div
            style={{
              padding: "14px 18px",
              borderBottom: "1px solid rgba(255,255,255,0.07)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "12px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ ...mono, fontSize: "11px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.4)" }}>
                LIVE AUDIT — /sse/audit
              </span>
              <span
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  ...mono,
                  fontSize: "10px",
                  color: auditUnavailable ? "#E5484D" : auditConnected ? "#3ECF8E" : "rgba(255,255,255,0.3)",
                }}
              >
                <span
                  style={{
                    width: "5px",
                    height: "5px",
                    borderRadius: "50%",
                    background: auditUnavailable ? "#E5484D" : auditConnected ? "#3ECF8E" : "rgba(255,255,255,0.3)",
                    animation: auditConnected && !auditPaused && !auditUnavailable ? "citadel-pulse 2.2s ease-in-out infinite" : "none",
                  }}
                />
                {auditUnavailable ? "UNAVAILABLE" : auditConnected ? (auditPaused ? "PAUSED" : "STREAMING") : "CONNECTING"}
              </span>
            </div>
            {!auditUnavailable && (
              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  onClick={toggleAuditPause}
                  className="btn-outline"
                  style={{ background: "transparent", ...mono, fontSize: "11px", padding: "5px 11px", borderRadius: "5px", cursor: "pointer" }}
                >
                  {auditPaused ? "Resume" : "Pause"}
                </button>
                <button
                  onClick={clearAudit}
                  className="btn-outline"
                  style={{ background: "transparent", ...mono, fontSize: "11px", padding: "5px 11px", borderRadius: "5px", cursor: "pointer" }}
                >
                  Clear
                </button>
              </div>
            )}
          </div>

          {/* Column headers — only when data is present */}
          {!auditUnavailable && auditRows.length > 0 && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "60px 120px 1fr 80px",
                gap: "10px",
                padding: "8px 18px",
                borderBottom: "1px solid rgba(255,255,255,0.05)",
                ...mono,
                fontSize: "10px",
                letterSpacing: "0.08em",
                color: "rgba(255,255,255,0.3)",
              }}
            >
              <span>TIME</span>
              <span>AGENT</span>
              <span>ACTION · LABEL</span>
              <span style={{ textAlign: "right" }}>OUTCOME</span>
            </div>
          )}

          {/* Audit body */}
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              minHeight: "320px",
              maxHeight: "400px",
              overflowY: "auto",
            }}
          >
            {auditUnavailable ? (
              <UnavailableMessage label="/sse/audit" />
            ) : auditRows.length === 0 ? (
              <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", ...mono, fontSize: "12px", color: "rgba(255,255,255,0.3)" }}>
                waiting for audit events…
              </div>
            ) : (
              auditRows.map((r) => <AuditFeedRow key={r.id} row={r} />)
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
