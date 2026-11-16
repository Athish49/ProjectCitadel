"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { useAdversarialStream } from "@/lib/hooks/use-adversarial-stream";
import { useAuditStream } from "@/lib/hooks/use-audit-stream";
import {
  ADVERSARY_HERO,
  ADVERSARY_SECTIONS,
  ADVERSARY_COST_COPY,
  ADVERSARY_PROFILE,
  ADVERSARY_AUDIT_LEGEND,
  ADVERSARY_CTA,
} from "@/lib/data/adversary";
import { AttemptFeedRow, AuditFeedRow, catNameFor, fmtRelative } from "@/components/adversary/feed-rows";

export function AdversaryView() {
  const rootRef = useRef<HTMLDivElement>(null);

  const {
    attempts,
    breachCount,
    lastBreachAt,
    totalAttempts,
    connected,
    backendDown,
    agentStatus,
    lastSeenAt,
  } = useAdversarialStream();

  const {
    rows: auditRows,
    connected: auditConnected,
    backendDown: auditBackendDown,
  } = useAuditStream();

  // Scroll-reveal — matches the design prototype's own componentDidMount
  // pattern: flip data-anim="on" on the page root (guarded by reduced-motion),
  // then observe every [data-rv] inside it, adding data-in once and
  // unobserving.
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    let reduce = false;
    try {
      reduce = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
    } catch {
      reduce = false;
    }
    if (reduce || !("IntersectionObserver" in window)) return;

    root.setAttribute("data-anim", "on");
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.setAttribute("data-in", "1");
            io.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.05 }
    );
    root.querySelectorAll("[data-rv]").forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  const latest = attempts[0];
  const focusCat = latest ? catNameFor(latest.attack_id) : null;

  const statusColor = backendDown
    ? "var(--alert)"
    : agentStatus === "LIVE"
    ? "var(--ok)"
    : agentStatus === "OFFLINE"
    ? "var(--warn)"
    : "rgba(255,255,255,0.6)";
  const displayStatus = backendDown ? "OFFLINE" : agentStatus;
  const isLivePulse = !backendDown && agentStatus === "LIVE";
  const agentSubtext = backendDown
    ? "backend unreachable"
    : agentStatus === "LIVE"
    ? focusCat
      ? `Testing ${focusCat}`
      : "Awaiting first attempt"
    : agentStatus === "OFFLINE"
    ? lastSeenAt
      ? `Last seen ${fmtRelative(lastSeenAt)}`
      : "No activity recorded"
    : "Connecting…";

  const feedState = backendDown ? "OFFLINE" : !connected ? "CONNECTING" : "STREAMING";
  const feedColor = backendDown
    ? "var(--alert)"
    : !connected
    ? "rgba(255,255,255,0.5)"
    : "var(--ok)";

  const auditState = auditBackendDown ? "OFFLINE" : !auditConnected ? "CONNECTING" : "STREAMING";
  const auditColor = auditBackendDown
    ? "var(--alert)"
    : !auditConnected
    ? "rgba(255,255,255,0.5)"
    : "var(--ok)";

  // Real derivation replacing the design's scripted fake "month" counter:
  // same $0.006/attempt assumption stated in the design's own copy, applied
  // to the real all-time attempt count from the DB.
  const cost = Math.min(ADVERSARY_COST_COPY.cap, totalAttempts * ADVERSARY_COST_COPY.costPerAttempt);
  const costW = ((cost / ADVERSARY_COST_COPY.cap) * 100).toFixed(1);

  return (
    <div ref={rootRef}>
      {/* Hero */}
      <section style={{ maxWidth: "1264px", margin: "0 auto", padding: "clamp(64px,9vw,120px) 32px 0" }}>
        <div data-rv className="eb">
          {ADVERSARY_HERO.eyebrow}
        </div>
        <h1
          data-rv
          style={{
            margin: "22px 0 0",
            fontSize: "clamp(40px,6.4vw,84px)",
            lineHeight: 1,
            letterSpacing: "-0.04em",
            fontWeight: 600,
            maxWidth: "900px",
            transitionDelay: "80ms",
          }}
        >
          {ADVERSARY_HERO.headline}
        </h1>
        <p
          data-rv
          style={{
            margin: "26px 0 0",
            maxWidth: "560px",
            fontSize: "clamp(17px,1.5vw,19px)",
            lineHeight: 1.5,
            color: "rgba(255,255,255,0.7)",
            transitionDelay: "160ms",
          }}
        >
          {ADVERSARY_HERO.lead}
        </p>

        <div
          data-rv
          style={{
            marginTop: "56px",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))",
            gap: "1px",
            background: "rgba(255,255,255,0.08)",
            border: "1px solid rgba(255,255,255,0.08)",
            transitionDelay: "240ms",
          }}
        >
          <div className="cell" style={{ padding: "24px 24px 26px" }}>
            <div className="eb" style={{ fontSize: "11px" }}>
              Attacks captured
            </div>
            <div
              className="mono"
              style={{ marginTop: "14px", fontSize: "38px", lineHeight: 1, fontWeight: 500, fontVariantNumeric: "tabular-nums" }}
            >
              {backendDown ? "—" : totalAttempts.toLocaleString("en-US")}
            </div>
            <div style={{ marginTop: "12px", fontSize: "13px", color: "rgba(255,255,255,0.58)" }}>
              {backendDown ? "waiting for backend" : "All time"}
            </div>
          </div>

          <div className="cell" style={{ padding: "24px 24px 26px" }}>
            <div className="eb" style={{ fontSize: "11px" }}>
              Successful breaches
            </div>
            <div
              className="mono"
              style={{
                marginTop: "14px",
                fontSize: "38px",
                lineHeight: 1,
                fontWeight: 500,
                // Attacker's-view stat: a breach evaded every layer — not
                // flagged as an attack — so it follows the same red/green
                // flip as the feed below it.
                color: backendDown ? "rgba(255,255,255,0.3)" : "var(--ok)",
              }}
            >
              {backendDown ? "—" : breachCount}
            </div>
            <div style={{ marginTop: "12px", fontSize: "13px", color: "rgba(255,255,255,0.58)" }}>
              {backendDown ? "waiting for backend" : lastBreachAt ? `A breach must evade all 7 layers · last ${fmtRelative(lastBreachAt)}` : "A breach must evade all 7 layers"}
            </div>
          </div>

          <div className="cell" style={{ padding: "24px 24px 26px" }}>
            <div className="eb" style={{ fontSize: "11px" }}>
              Agent status
            </div>
            <div style={{ marginTop: "14px", display: "flex", alignItems: "center", gap: "12px" }}>
              <span
                className={isLivePulse ? "live-dot" : undefined}
                style={
                  isLivePulse
                    ? undefined
                    : { width: "7px", height: "7px", borderRadius: "50%", background: statusColor, display: "inline-block" }
                }
              />
              <span className="mono" style={{ fontSize: "38px", lineHeight: 1, fontWeight: 500, color: statusColor }}>
                {displayStatus}
              </span>
            </div>
            <div style={{ marginTop: "12px", fontSize: "13px", color: "rgba(255,255,255,0.58)" }}>{agentSubtext}</div>
          </div>
        </div>
        <div data-rv className="mono" style={{ padding: "14px 0 0", fontSize: "12px", color: "rgba(255,255,255,0.55)" }}>
          {ADVERSARY_HERO.sandboxNote}
        </div>
      </section>

      {/* Attacker's view */}
      <section className="sec">
        <div data-rv>
          <div className="eb">{ADVERSARY_SECTIONS.attacker.eyebrow}</div>
          <h2 className="h2">{ADVERSARY_SECTIONS.attacker.heading}</h2>
        </div>
        <div data-rv style={{ marginTop: "32px", display: "flex", flexWrap: "wrap", gap: "24px", alignItems: "flex-start" }}>
          {/* Live feed */}
          <div className="panel" style={{ flex: "2 1 520px", minWidth: 0 }}>
            <div className="ph">
              <span style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span className="eb" style={{ fontSize: "11px" }}>
                  Live feed
                </span>
                <span className="mono" style={{ fontSize: "11.5px", letterSpacing: "0.1em", color: feedColor }}>
                  {feedState}
                </span>
              </span>
            </div>
            <div style={{ minHeight: "420px", maxHeight: "560px", overflowY: "auto" }}>
              {attempts.length === 0 ? (
                <div className="mono" style={{ padding: "22px 18px", fontSize: "12.5px", color: "rgba(255,255,255,0.58)" }}>
                  {backendDown ? "Backend unavailable — no data to display" : "Waiting for attack attempts…"}
                </div>
              ) : (
                attempts.map((a) => <AttemptFeedRow key={a.trace_id} attempt={a} />)
              )}
            </div>
          </div>

          {/* Sidebar: cost + profile */}
          <div style={{ flex: "1 1 300px", minWidth: 0, display: "flex", flexDirection: "column", gap: "24px" }}>
            <div className="panel" style={{ padding: "20px 20px 22px" }}>
              <div className="eb" style={{ fontSize: "11px" }}>
                {ADVERSARY_COST_COPY.label}
              </div>
              <div className="mono" style={{ marginTop: "12px", fontSize: "24px", lineHeight: 1, fontWeight: 500 }}>
                ${cost.toFixed(2)}{" "}
                <span style={{ fontSize: "14px", color: "rgba(255,255,255,0.58)" }}>
                  / ${ADVERSARY_COST_COPY.cap.toFixed(2)} cap
                </span>
              </div>
              <div style={{ marginTop: "14px", height: "4px", background: "rgba(255,255,255,0.1)" }}>
                <div data-grow style={{ height: "4px", width: `${costW}%`, background: "var(--ok)" }} />
              </div>
              <p style={{ margin: "14px 0 0", fontSize: "13.5px", color: "rgba(255,255,255,0.68)" }}>
                {ADVERSARY_COST_COPY.note}
              </p>
            </div>

            <div className="panel">
              <div className="ph" style={{ padding: "13px 20px" }}>
                <span className="eb" style={{ fontSize: "11px" }}>
                  {ADVERSARY_PROFILE.heading}
                </span>
              </div>
              {ADVERSARY_PROFILE.rows.map((row) => (
                <div
                  key={row.label}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: "16px",
                    padding: "11px 20px",
                    borderBottom: "1px solid rgba(255,255,255,0.06)",
                    fontSize: "13.5px",
                  }}
                >
                  <span style={{ color: "rgba(255,255,255,0.62)" }}>{row.label}</span>
                  <span style={{ textAlign: "right" }}>{row.value}</span>
                </div>
              ))}
              <div style={{ padding: "8px 20px" }}>
                <a
                  className="mono"
                  href={ADVERSARY_PROFILE.codeRefHref}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ fontSize: "12.5px", display: "inline-flex", alignItems: "center", minHeight: "44px" }}
                >
                  {ADVERSARY_PROFILE.codeRefLabel}
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Defender's view */}
      <section className="sec">
        <div data-rv>
          <div className="eb">{ADVERSARY_SECTIONS.defender.eyebrow}</div>
          <h2 className="h2">{ADVERSARY_SECTIONS.defender.heading}</h2>
          <p className="lead">{ADVERSARY_SECTIONS.defender.lead}</p>
        </div>
        <div data-rv className="panel" style={{ marginTop: "32px", overflowX: "auto" }}>
          <div style={{ minWidth: "760px" }}>
            <div className="ph">
              <span style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span className="eb" style={{ fontSize: "11px" }}>
                  Live audit
                </span>
                <span className="mono" style={{ fontSize: "11.5px", letterSpacing: "0.1em", color: auditColor }}>
                  {auditState}
                </span>
              </span>
              <span className="mono" style={{ fontSize: "11.5px", color: "rgba(255,255,255,0.58)" }}>
                {ADVERSARY_AUDIT_LEGEND}
              </span>
            </div>
            <div
              className="eb"
              style={{
                display: "grid",
                gridTemplateColumns: "80px 96px 48px 150px 1fr 90px",
                gap: "12px",
                padding: "11px 18px",
                fontSize: "11px",
                borderBottom: "1px solid rgba(255,255,255,0.08)",
              }}
            >
              <span>Time</span>
              <span>Trace</span>
              <span>Src</span>
              <span>Agent</span>
              <span>Action · label</span>
              <span style={{ textAlign: "right" }}>Outcome</span>
            </div>
            <div style={{ minHeight: "330px", maxHeight: "460px", overflowY: "auto" }}>
              {auditRows.length === 0 ? (
                <div className="mono" style={{ padding: "22px 18px", fontSize: "12.5px", color: "rgba(255,255,255,0.58)" }}>
                  {auditBackendDown ? "Backend unavailable — no data to display" : "Waiting for audit events…"}
                </div>
              ) : (
                auditRows.map((r) => <AuditFeedRow key={r.id} row={r} />)
              )}
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ marginTop: "clamp(88px,10vw,140px)", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
        <div
          data-rv
          style={{
            maxWidth: "1264px",
            margin: "0 auto",
            padding: "clamp(72px,9vw,120px) 32px",
            display: "flex",
            flexWrap: "wrap",
            alignItems: "flex-end",
            justifyContent: "space-between",
            gap: "32px 64px",
          }}
        >
          <h2
            style={{
              margin: 0,
              fontSize: "clamp(30px,4.2vw,54px)",
              lineHeight: 1.04,
              letterSpacing: "-0.035em",
              fontWeight: 600,
              maxWidth: "680px",
            }}
          >
            {ADVERSARY_CTA.heading}
          </h2>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "12px" }}>
            <Link className="btn btn-p" href={ADVERSARY_CTA.primary.href}>
              {ADVERSARY_CTA.primary.label}
            </Link>
            <Link className="btn btn-g" href={ADVERSARY_CTA.secondary.href}>
              {ADVERSARY_CTA.secondary.label}
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
