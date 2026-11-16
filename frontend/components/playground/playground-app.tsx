"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Nav } from "@/components/layout/nav";
import { Footer } from "@/components/layout/footer";
import { usePlaygroundStream } from "@/lib/hooks/use-playground-stream";
import { LAYER_DEFINITIONS, humanizePolicyHeld } from "@/lib/types/playground";
import {
  PERSONAS,
  COMPOSER_CATEGORIES,
  buildTemplates,
  money,
  type Persona,
  type ComposerCategory,
  type PlaygroundTemplate,
} from "@/lib/data/playground";
import styles from "./playground.module.css";

// ── Types ─────────────────────────────────────────────────────────────────

interface Message {
  who: string; // display name shown above the bubble: first name | "Assistant" | "Pipeline" | "Error"
  from: "user" | "assistant" | "pipeline" | "error";
  text: string;
}

interface ProfileRecord {
  first_name?: string;
  last_name?: string;
  city?: string;
  state?: string;
  policy_number?: string;
  policy_type?: string;
  policy_csl?: string;
  policy_deductible?: number;
  coverage_type?: string;
  policy_expiry_date?: string;
  policy_status?: string;
  auto_make?: string;
  auto_model?: string;
  auto_year?: number;
  claim_number?: string;
  incident_type?: string;
  claim_stage?: string;
  total_claim_amount?: number;
}

function greetingFor(persona: Persona): Message {
  const first = persona.name.split(" ")[0];
  return {
    who: "Assistant",
    from: "assistant",
    text: `Hi ${first}, I can answer questions about your policy and claim ${persona.claimNumber}, or help you file a new one.`,
  };
}

function fmtDate(iso: string | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-US", { day: "2-digit", month: "short", year: "numeric" });
}

function tabOn(on: boolean) {
  return { color: on ? "#ffffff" : "rgba(255,255,255,0.62)", borderBottomColor: on ? "#f4f4f5" : "transparent" };
}

export function PlaygroundApp() {
  const [personaIdx, setPersonaIdx] = useState(0);
  const persona = PERSONAS[personaIdx];
  const templates = buildTemplates(persona, PERSONAS);

  const [profile, setProfile] = useState<ProfileRecord | null>(null);
  const [category, setCategory] = useState<ComposerCategory>(0);
  const [messages, setMessages] = useState<Message[]>([greetingFor(PERSONAS[0])]);
  const [draft, setDraft] = useState("");
  const [suppressTrace, setSuppressTrace] = useState(false);

  const chatSessionId = useRef<string>(
    typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : String(Math.random())
  );
  const hasAttachment = useRef(false);
  const verdictKeyRef = useRef<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  const { trace, isStreaming, error, submit } = usePlaygroundStream();
  const liveTrace = suppressTrace ? null : trace;

  // ── Fetch the real "on file" record for the active persona ───────────────
  useEffect(() => {
    let cancelled = false;
    setProfile(null);
    fetch(`/api/playground/profile/${persona.key}`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!cancelled && data) setProfile(data);
      })
      .catch(() => {
        /* fall back to the static persona record rendered below */
      });
    return () => {
      cancelled = true;
    };
  }, [persona.key]);

  // ── Scroll-reveal for the hero (matches every other redesigned page) ─────
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (!("IntersectionObserver" in window) || reduce) return;
    root.setAttribute("data-anim", "on");
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.setAttribute("data-in", "1");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.05 }
    );
    root.querySelectorAll("[data-rv]").forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  // When a verdict lands, surface it in the conversation exactly once.
  useEffect(() => {
    if (!trace?.verdict || !trace?.traceId) return;
    const key = `${trace.traceId}:${trace.verdict.outcome}`;
    if (verdictKeyRef.current === key) return;
    verdictKeyRef.current = key;
    const v = trace.verdict;
    if (v.outcome === "BLOCKED") {
      setMessages((prev) => [...prev, { who: "Pipeline", from: "pipeline", text: v.summary }]);
    } else if (v.outcome === "ERROR") {
      setMessages((prev) => [...prev, { who: "Error", from: "error", text: v.summary }]);
    } else {
      setMessages((prev) => [...prev, { who: "Assistant", from: "assistant", text: v.summary }]);
    }
  }, [trace?.verdict, trace?.traceId]);

  // ── Actions ────────────────────────────────────────────────────────────

  function pickPersona(i: number) {
    if (i === personaIdx) return;
    setPersonaIdx(i);
    setMessages([greetingFor(PERSONAS[i])]);
    setDraft("");
    setCategory(0);
    hasAttachment.current = false;
    verdictKeyRef.current = null;
    setSuppressTrace(true);
    chatSessionId.current = crypto.randomUUID();
  }

  function newSession() {
    setMessages([greetingFor(persona)]);
    setDraft("");
    hasAttachment.current = false;
    verdictKeyRef.current = null;
    setSuppressTrace(true);
    chatSessionId.current = crypto.randomUUID();
  }

  function sendDraft() {
    const text = draft.trim();
    if (!text || isStreaming) return;
    setMessages((prev) => [...prev, { who: persona.name.split(" ")[0], from: "user", text }]);
    setDraft("");
    setSuppressTrace(false);
    submit(text, "chat", "intake", "live", undefined, {
      chatSessionId: chatSessionId.current,
      personaKey: persona.key,
      hasAttachment: hasAttachment.current,
    });
  }

  function runTemplate(tpl: PlaygroundTemplate) {
    if (isStreaming) return;
    const bubbleText = tpl.fileName ? `FILE · ${tpl.fileName}` : tpl.payload;
    setMessages((prev) => [...prev, { who: persona.name.split(" ")[0], from: "user", text: bubbleText }]);
    setDraft("");
    setSuppressTrace(false);
    if (tpl.composerTab === "pdf" || tpl.composerTab === "image") hasAttachment.current = true;
    submit(
      tpl.payload,
      tpl.composerTab,
      "intake",
      "live",
      tpl.attackId && tpl.attackName ? { id: tpl.attackId, name: tpl.attackName } : undefined,
      {
        chatSessionId: chatSessionId.current,
        personaKey: persona.key,
        hasAttachment: hasAttachment.current,
      }
    );
  }

  function openFilesTab() {
    setCategory(3);
  }

  // ── Derived display state ────────────────────────────────────────────────

  const first = persona.name.split(" ")[0];
  const running = isStreaming;

  const vehicle = profile?.auto_year
    ? `${profile.auto_year} ${profile.auto_make} ${profile.auto_model}`
    : persona.vehicle;
  const owner =
    profile?.first_name && profile?.last_name ? `${profile.first_name} ${profile.last_name}` : persona.name;
  const policyRows: [string, string][] = profile
    ? [
        ["Type", (profile.policy_type ?? "").replace(/_/g, " ")],
        ["Tier", profile.coverage_type ?? "—"],
        ["Status", profile.policy_status ?? "—"],
        ["Coverage limit", profile.policy_csl ?? "—"],
        ["Deductible", profile.policy_deductible != null ? money(profile.policy_deductible, 0) : "—"],
        ["Expires", fmtDate(profile.policy_expiry_date)],
      ]
    : [
        ["Type", persona.policyType.replace(/_/g, " ")],
        ["Tier", persona.coverageType],
        ["Status", persona.policyStatus],
        ["Coverage limit", persona.policyCsl],
        ["Deductible", money(persona.policyDeductible, 0)],
        ["Expires", fmtDate(persona.policyExpiry)],
      ];
  const claimRows: [string, string][] = profile
    ? [
        ["Number", profile.claim_number ?? "—"],
        ["Stage", (profile.claim_stage ?? "").replace(/_/g, " ")],
        ["Incident", profile.incident_type ?? "—"],
        ["Amount", profile.total_claim_amount != null ? money(profile.total_claim_amount, 2) : "—"],
      ]
    : [
        ["Number", persona.claimNumber],
        ["Stage", persona.claimStage.replace(/_/g, " ")],
        ["Incident", persona.incidentType],
        ["Amount", money(persona.totalClaimAmount, 2)],
      ];

  // Live 7-layer trace, indexed identically to LAYER_DEFINITIONS. Every status
  // shown here is read directly off the backend-reported layer — once a
  // verdict lands, `liveTrace.layers` has already been replaced wholesale with
  // the backend's authoritative verdict.layers (see use-playground-stream.ts),
  // so nothing here is inferred from the verdict outcome.
  const verdict = liveTrace?.verdict ?? null;
  const layerRows = LAYER_DEFINITIONS.map((def, i) => {
    const l = liveTrace?.layers[i];
    let status = "—";
    let color = "rgba(255,255,255,.55)";
    let detail = "";
    let bg = "transparent";
    let opacity = 1;

    if (l) {
      if (l.status === "passed") {
        // Not flagged as an attack — a clean, good request. Green.
        status = "PASS";
        color = "var(--ok)";
        detail = l.events[0]?.message ?? "";
      } else if (l.status === "blocked") {
        // Detected and stopped as an attack. Red.
        status = "BLOCKED";
        color = "var(--alert)";
        bg = "rgba(229,72,77,.09)";
        detail = l.events[0]?.message ?? "";
      } else if (l.status === "held") {
        // Declined per policy boundary — still a detected/refused request. Red.
        status = "HELD";
        color = "var(--alert)";
        bg = "rgba(229,72,77,.09)";
        detail = verdict?.policyHeld ? humanizePolicyHeld(verdict.policyHeld) : (l.events[0]?.message ?? "");
      } else if (l.status === "error") {
        status = "ERROR";
        color = "var(--alert)";
        bg = "rgba(229,72,77,.08)";
        detail = l.events[0]?.message ?? "Layer failed — check skipped.";
      } else if (l.status === "skipped") {
        status = "SKIPPED";
        color = "var(--warn)";
        detail = l.events[0]?.message ?? "";
      } else if (l.status === "running") {
        status = "RUNNING";
        color = "#ffffff";
      } else if (l.status === "not_reached") {
        status = "NOT REACHED";
        opacity = 0.5;
      } else if (l.status === "pending") {
        opacity = 0.6;
      }
    }
    return { n: String(i + 1).padStart(2, "0"), name: def.name, status, color, detail, bg, opacity };
  });

  // Colour rule (flipped from the original green-for-defended convention):
  // red = this request was detected/flagged/stopped as an attack (BLOCKED,
  // HELD); green = it was not flagged — a clean, good request (CLEAN).
  const blockedLayerIdx = verdict?.blockedByLayer ? LAYER_DEFINITIONS.findIndex((l) => l.id === verdict.blockedByLayer) : -1;
  const chip = running
    ? { text: "RUNNING", fg: "#ffffff", bd: "rgba(255,255,255,.45)", bg: "transparent" }
    : verdict?.outcome === "BLOCKED"
    ? {
        text: blockedLayerIdx >= 0 ? `BLOCKED AT ${String(blockedLayerIdx + 1).padStart(2, "0")}` : "BLOCKED",
        fg: "var(--alert)",
        bd: "rgba(229,72,77,.5)",
        bg: "rgba(229,72,77,.08)",
      }
    : verdict?.outcome === "HELD"
    ? // The actor model itself held a policy boundary — the request was
      // still flagged/declined, so it gets the same red "attack detected"
      // treatment as BLOCKED.
      { text: "DEFENDED", fg: "var(--alert)", bd: "rgba(229,72,77,.5)", bg: "rgba(229,72,77,.08)" }
    : verdict?.outcome === "ERROR"
    ? { text: "ERROR", fg: "var(--alert)", bd: "rgba(229,72,77,.5)", bg: "rgba(229,72,77,.08)" }
    : verdict?.outcome === "CLEAN"
    ? { text: "ANSWERED", fg: "var(--ok)", bd: "rgba(62,207,142,.5)", bg: "rgba(62,207,142,.08)" }
    : { text: "IDLE", fg: "rgba(255,255,255,.6)", bd: "rgba(255,255,255,.14)", bg: "transparent" };

  const totalLayers = LAYER_DEFINITIONS.length;
  const evaluatedCount =
    liveTrace?.layers.filter((l) => l.status !== "pending" && l.status !== "running" && l.status !== "not_reached")
      .length ?? 0;
  const runningIdx = liveTrace?.layers.findIndex((l) => l.status === "running") ?? -1;
  // Factual, trace-level summary — deliberately never repeats verdict.summary,
  // which is the reply text already shown verbatim in the Conversation pane.
  const traceNote = running
    ? `Streaming layer ${Math.min(totalLayers, (runningIdx >= 0 ? runningIdx : evaluatedCount) + 1)} of ${totalLayers}.`
    : verdict
    ? verdict.outcome === "BLOCKED"
      ? `Stopped by ${verdict.blockedByPattern ?? verdict.blockedByLayer ?? "a defense layer"}. ${evaluatedCount}/${totalLayers} layers evaluated.`
      : verdict.outcome === "HELD"
      ? `Held at the Actor LLM layer: ${verdict.policyHeld ? humanizePolicyHeld(verdict.policyHeld).replace(/^Declined — /, "") : "policy boundary"}. ${evaluatedCount}/${totalLayers} layers evaluated.`
      : verdict.outcome === "ERROR"
      ? `Pipeline error${verdict.blockedByLayer ? ` at ${verdict.blockedByLayer}` : ""} — request not completed. ${evaluatedCount}/${totalLayers} layers evaluated.`
      : `${evaluatedCount}/${totalLayers} layers evaluated.`
    : "Send a message to start a trace.";

  const filteredTemplates = templates.filter((t) => t.category === category);

  return (
    <div data-page="playground" ref={rootRef} style={{ minHeight: "100vh" }}>
      <Nav />

      <main>
        <section className="sec" style={{ paddingBottom: 0 }}>
          <div data-rv className="eb">
            Playground
          </div>
          <h1
            data-rv
            style={{
              margin: "22px 0 0",
              fontSize: "clamp(40px,6.4vw,84px)",
              lineHeight: 1,
              letterSpacing: "-0.04em",
              fontWeight: 600,
              maxWidth: 900,
              transitionDelay: "80ms",
            }}
          >
            Try to break it.
          </h1>
          <p
            data-rv
            style={{
              margin: "26px 0 0",
              maxWidth: 600,
              fontSize: "clamp(17px,1.5vw,19px)",
              lineHeight: 1.5,
              color: "rgba(255,255,255,.7)",
              transitionDelay: "160ms",
            }}
          >
            A working claims assistant behind seven defence layers. Sign in as a customer, ask or attack, and watch
            each layer decide.
          </p>

          {error && (
            <div
              style={{
                marginTop: 24,
                padding: "10px 16px",
                border: "1px solid rgba(229,72,77,.4)",
                background: "rgba(229,72,77,.08)",
                color: "var(--alert)",
                fontSize: 13,
                borderRadius: 4,
              }}
              className="mono"
            >
              {error}
            </div>
          )}

          <div data-rv className="panel" style={{ marginTop: 56, transitionDelay: "240ms" }}>
            {/* Persona picker */}
            <div
              style={{
                padding: "4px 24px",
                borderBottom: "1px solid rgba(255,255,255,.08)",
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                gap: "4px 28px",
              }}
            >
              <span className="eb" style={{ fontSize: 11 }}>
                Signed in as
              </span>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "0 24px", flex: "1 1 auto" }}>
                {PERSONAS.map((p, i) => (
                  <button
                    key={p.key}
                    type="button"
                    className={styles.tab}
                    onClick={() => pickPersona(i)}
                    aria-pressed={i === personaIdx}
                    style={tabOn(i === personaIdx)}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
              <button
                type="button"
                className={styles.tab}
                onClick={newSession}
                style={{ fontSize: 13, color: "rgba(255,255,255,.62)" }}
              >
                New session
              </button>
            </div>

            {/* 3-column app body */}
            <div style={{ display: "flex", flexWrap: "wrap" }}>
              {/* On file */}
              <div
                style={{
                  flex: ".75 1 240px",
                  minWidth: 0,
                  padding: "28px 24px",
                  borderRight: "1px solid rgba(255,255,255,.08)",
                }}
              >
                <div className="eb" style={{ fontSize: 11 }}>
                  On file
                </div>
                <div style={{ marginTop: 14, fontSize: 22, lineHeight: 1.2, letterSpacing: "-0.02em", fontWeight: 600 }}>
                  {vehicle}
                </div>
                <div style={{ marginTop: 4, fontSize: 13.5, color: "rgba(255,255,255,.62)" }}>{owner}</div>

                <div style={{ marginTop: 28 }}>
                  <div className="eb" style={{ fontSize: 11 }}>
                    Policy
                  </div>
                  <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 9 }}>
                    {policyRows.map(([k, v]) => (
                      <div key={k} className={styles.kv}>
                        <span style={{ color: "rgba(255,255,255,.62)" }}>{k}</span>
                        <span style={{ textAlign: "right", color: "rgba(255,255,255,.92)" }}>{v}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{ marginTop: 28 }}>
                  <div className="eb" style={{ fontSize: 11 }}>
                    Claim
                  </div>
                  <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 9 }}>
                    {claimRows.map(([k, v]) => (
                      <div key={k} className={styles.kv}>
                        <span style={{ color: "rgba(255,255,255,.62)" }}>{k}</span>
                        <span style={{ textAlign: "right", color: "rgba(255,255,255,.92)" }}>{v}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <p style={{ margin: "28px 0 0", fontSize: 12.5, lineHeight: 1.5, color: "rgba(255,255,255,.55)" }}>
                  Exactly what the assistant knows. Check its answers against it.
                </p>
              </div>

              {/* Conversation */}
              <div
                style={{
                  flex: "1.5 1 420px",
                  minWidth: 0,
                  borderRight: "1px solid rgba(255,255,255,.08)",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <div style={{ padding: "28px 24px 0" }}>
                  <span className="eb" style={{ fontSize: 11 }}>
                    Conversation
                  </span>
                </div>
                <div
                  ref={scrollRef}
                  style={{
                    padding: "20px 24px",
                    display: "flex",
                    flexDirection: "column",
                    gap: 16,
                    minHeight: 340,
                    maxHeight: 480,
                    overflowY: "auto",
                    flexGrow: 1,
                  }}
                >
                  {messages.map((m, i) => {
                    const isUser = m.from === "user";
                    const isPipeline = m.from === "pipeline"; // BLOCKED — detected as an attack, so red (flipped from green).
                    const isError = m.from === "error";
                    const bg = isUser
                      ? "#f4f4f5"
                      : isPipeline
                      ? "rgba(229,72,77,.08)"
                      : isError
                      ? "rgba(229,72,77,.08)"
                      : "#131417";
                    const bd = isPipeline
                      ? "rgba(229,72,77,.4)"
                      : isError
                      ? "rgba(229,72,77,.4)"
                      : isUser
                      ? "#f4f4f5"
                      : "rgba(255,255,255,.08)";
                    const fg = isUser
                      ? "#0a0b0c"
                      : isPipeline
                      ? "var(--alert)"
                      : isError
                      ? "var(--alert)"
                      : "rgba(255,255,255,.92)";
                    return (
                      <div
                        key={i}
                        className={styles.msgIn}
                        style={{ alignSelf: isUser ? "flex-end" : "flex-start", maxWidth: "84%" }}
                      >
                        <div
                          style={{
                            fontSize: 12,
                            color: "rgba(255,255,255,.55)",
                            marginBottom: 5,
                            textAlign: isUser ? "right" : "left",
                          }}
                        >
                          {m.who}
                        </div>
                        <div
                          style={{
                            padding: "11px 14px",
                            borderRadius: 8,
                            fontSize: 14.5,
                            lineHeight: 1.5,
                            background: bg,
                            border: `1px solid ${bd}`,
                            color: fg,
                            wordBreak: "break-word",
                            overflowWrap: "anywhere",
                          }}
                        >
                          {m.text}
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div style={{ padding: "0 24px 24px" }}>
                  <div className={styles.comp}>
                    <button type="button" className={styles.icon} onClick={openFilesTab} aria-label="Attach a file">
                      <svg aria-hidden="true" width="18" height="18" viewBox="0 0 18 18" style={{ fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round" }}>
                        <path d="M9 3.5v11M3.5 9h11" />
                      </svg>
                    </button>
                    <textarea
                      className={styles.cin}
                      rows={1}
                      aria-label="Message"
                      placeholder={`Message as ${first}…`}
                      value={draft}
                      onChange={(e) => setDraft(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          sendDraft();
                        }
                      }}
                    />
                    <button
                      className="btn btn-p"
                      type="button"
                      onClick={sendDraft}
                      disabled={running || !draft.trim()}
                      style={{ minHeight: 40, height: 40, padding: "0 16px", opacity: running || !draft.trim() ? 0.5 : 1 }}
                    >
                      Send
                    </button>
                  </div>
                </div>
              </div>

              {/* Defence trace */}
              <div style={{ flex: "1 1 320px", minWidth: 0, padding: "28px 24px", display: "flex", flexDirection: "column" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, minHeight: 24 }}>
                  <span className="eb" style={{ fontSize: 11 }}>
                    Defence trace
                  </span>
                  <span
                    className="mono"
                    style={{
                      fontSize: 11,
                      letterSpacing: "0.08em",
                      padding: "3px 8px",
                      borderRadius: 4,
                      border: `1px solid ${chip.bd}`,
                      color: chip.fg,
                      background: chip.bg,
                      transition: "all .3s",
                    }}
                  >
                    {chip.text}
                  </span>
                </div>
                <div style={{ marginTop: 16, display: "flex", flexDirection: "column", gap: 2 }}>
                  {layerRows.map((l) => (
                    <div
                      key={l.n}
                      style={{
                        padding: "9px 10px",
                        margin: "0 -10px",
                        borderRadius: 6,
                        background: l.bg,
                        opacity: l.opacity,
                        transition: "opacity .3s,background .3s",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
                        <span className="mono" style={{ fontSize: 12, color: "rgba(255,255,255,.55)", flex: "0 0 18px" }}>
                          {l.n}
                        </span>
                        <span style={{ flex: "1 1 auto", fontSize: 14.5 }}>{l.name}</span>
                        <span className="mono" style={{ fontSize: 11, letterSpacing: "0.06em", color: l.color }}>
                          {l.status}
                        </span>
                      </div>
                      <div style={{ margin: "2px 0 0 30px", fontSize: 12.5, lineHeight: 1.4, color: "rgba(255,255,255,.58)", minHeight: 18, wordBreak: "break-word" }}>
                        {l.detail}
                      </div>
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: "auto", paddingTop: 18, fontSize: 12.5, color: "rgba(255,255,255,.58)" }}>
                  {traceNote}
                </div>
              </div>
            </div>

            {/* Try a prompt */}
            <div style={{ borderTop: "1px solid rgba(255,255,255,.08)", background: "#08090a", padding: "8px 24px 22px" }}>
              <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "0 28px" }}>
                <span className="eb" style={{ fontSize: 11 }}>
                  Try a prompt
                </span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0 24px" }}>
                  {COMPOSER_CATEGORIES.map((name, i) => (
                    <button
                      key={name}
                      type="button"
                      className={styles.tab}
                      onClick={() => setCategory(i as ComposerCategory)}
                      aria-pressed={i === category}
                      style={{ fontSize: 13.5, ...tabOn(i === category) }}
                    >
                      {name}
                    </button>
                  ))}
                </div>
              </div>
              <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 8 }}>
                {filteredTemplates.map((t) => {
                  const isAttack = t.attackId != null;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      className="pick"
                      disabled={running}
                      onClick={() => runTemplate(t)}
                      title={isAttack ? "Adversarial example" : undefined}
                      aria-label={isAttack ? `${t.label} (adversarial example)` : undefined}
                      style={{
                        fontSize: 13.5,
                        minHeight: 44,
                        padding: "0 14px",
                        background: "#0c0d0f",
                        opacity: running ? 0.5 : 1,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: isAttack ? 7 : 0,
                      }}
                    >
                      {isAttack && (
                        // Attack/adversarial sample — red, not purple, so it
                        // reads as "this gets flagged/blocked" at a glance.
                        <span
                          aria-hidden="true"
                          style={{
                            width: 6,
                            height: 6,
                            borderRadius: "50%",
                            background: "var(--alert)",
                            flexShrink: 0,
                          }}
                        />
                      )}
                      {t.label}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <p data-rv style={{ margin: "16px 0 0", fontSize: 13, color: "rgba(255,255,255,.58)" }}>
            This is the live playground — every message runs the real seven-layer pipeline and writes a trace to
            the audit log.
          </p>
        </section>

        <section style={{ marginTop: "clamp(80px,9vw,120px)", borderTop: "1px solid rgba(255,255,255,.08)" }}>
          <div
            data-rv
            style={{
              maxWidth: 1264,
              margin: "0 auto",
              padding: "clamp(56px,7vw,96px) 32px",
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "24px 64px",
            }}
          >
            <h2 style={{ margin: 0, fontSize: "clamp(26px,3.4vw,40px)", lineHeight: 1.08, letterSpacing: "-0.03em", fontWeight: 600 }}>
              Found a gap? It becomes a public issue.
            </h2>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
              <Link className="btn btn-p" href="/matrix">
                See all 79 attack classes
              </Link>
              <Link className="btn btn-g" href="/adversary">
                Watch the adversarial agent
              </Link>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
