"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { SITE_LINKS } from "@/components/layout/page-nav";
import {
  PERSONAS,
  PG_LAYER_DEFS,
  makeTemplates,
  type Persona,
  type LayerKind,
  type TemplateSpec,
} from "@/lib/data/playground";

interface Message {
  who: string;
  from: "user" | "agent";
  isText: boolean;
  isFile: boolean;
  text?: string;
  fileName?: string;
  time: string;
}

interface LayerState {
  detail: string;
  kind: LayerKind;
}

interface AuditRow {
  tag: string;
  color: string;
  elapsed: string;
}

interface Verdict {
  label: "BLOCKED" | "ALLOWED";
  detail: string;
  audits: string;
}

interface RunSpec {
  blockAt: number;
  details: [string, LayerKind][];
  agentReply: string;
  verdictDetail: string;
}

const PERSONA: Persona = PERSONAS[0];

export function PlaygroundApp() {
  const p = PERSONA;
  const templates = makeTemplates(p);
  const first = p.name.split(" ")[0];
  const pathname = usePathname();

  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [running, setRunning] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [layerStates, setLayerStates] = useState<LayerState[]>([]);
  const [verdict, setVerdict] = useState<Verdict | null>(null);
  const [traceId, setTraceId] = useState("—");
  const [auditRows, setAuditRows] = useState<AuditRow[]>([]);
  const [copied, setCopied] = useState(false);
  const [activeCategory, setActiveCategory] = useState<"text" | "pdf" | "image">("text");

  const traceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const thinkTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setMessages([{
      who: "Assistant",
      from: "agent",
      isText: true,
      isFile: false,
      text: `Hi ${first}, I can help file a new claim or answer questions about ${p.claim}. What’s going on?`,
      time: "now",
    }]);
    return () => {
      if (traceTimer.current) clearTimeout(traceTimer.current);
      if (thinkTimer.current) clearTimeout(thinkTimer.current);
    };
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, thinking]);

  function pushMessage(msg: Omit<Message, "time">) {
    setMessages((prev) => [...prev, { ...msg, time: "now" }]);
  }

  function run(userBubble: Omit<Message, "time">, spec: RunSpec) {
    if (running) return;
    if (traceTimer.current) clearTimeout(traceTimer.current);
    if (thinkTimer.current) clearTimeout(thinkTimer.current);

    const newTraceId = "tr_" + Math.random().toString(36).slice(2, 10);
    pushMessage(userBubble);
    setRunning(true);
    setThinking(false);
    setLayerStates([]);
    setVerdict(null);
    setTraceId(newTraceId);
    setAuditRows([]);
    setDraft("");

    const t0 = Date.now();
    const tagMap: Record<LayerKind, [string, string]> = {
      pass: ["layer_pass", "#3ECF8E"],
      detect: ["pattern_detected", "#E2A336"],
      block: ["defense_fired", "#E5484D"],
    };

    const step = (i: number) => {
      const stopAt = spec.blockAt > 0 ? spec.blockAt : 7;
      if (i >= stopAt) {
        const vd: Verdict = {
          label: spec.blockAt > 0 ? "BLOCKED" : "ALLOWED",
          detail: spec.verdictDetail,
          audits: `${spec.details.length + (spec.blockAt > 0 ? 1 : 2)} audit rows written, chain intact`,
        };
        setRunning(false);
        setVerdict(vd);
        setThinking(true);
        thinkTimer.current = setTimeout(() => {
          setThinking(false);
          pushMessage({ who: "Assistant", from: "agent", isText: true, isFile: false, text: spec.agentReply });
        }, 650);
        return;
      }
      const [detail, kind] = spec.details[i];
      const elapsed = ((Date.now() - t0) / 1000).toFixed(2) + "s";
      const [tag, color] = tagMap[kind];
      setLayerStates((prev) => [...prev, { detail, kind }]);
      setAuditRows((prev) => [...prev, { tag, color, elapsed }]);
      traceTimer.current = setTimeout(() => step(i + 1), 480);
    };
    step(0);
  }

  function runTemplate(spec: TemplateSpec) {
    const bubble: Omit<Message, "time"> =
      spec.kind === "text"
        ? { who: p.name, from: "user", isText: true, isFile: false, text: spec.userText }
        : { who: p.name, from: "user", isText: false, isFile: true, fileName: spec.fileName };
    run(bubble, spec);
  }

  function classifyFreeText(text: string): RunSpec {
    const low = text.toLowerCase();
    if (/ignore (all|prior|previous)|you are now|act as|system:|bypass/.test(low)) {
      return {
        blockAt: 3,
        details: [
          ["NFKC normalised, scanning for zero-width chars", "pass"],
          ["pattern match: instruction_override", "detect"],
          ["semantic classifier - adversarial confidence 0.9 or higher", "block"],
        ],
        agentReply: "I can't action that - it reads like an attempt to override my instructions. Happy to help with your actual claim.",
        verdictDetail: "BLOCKED - Layer 3 semantic_classifier",
      };
    }
    if (/score_fraud|fraud score|risk score|risk factors/.test(low)) {
      return {
        blockAt: 6,
        details: [
          ["NFKC normalised, 0 zero-width chars stripped", "pass"],
          ["pattern match: privileged_tool_request", "detect"],
          ["adversarial score 0.5, below threshold - logged as signal only", "pass"],
          ["wrapped in untrusted-content delimiters", "pass"],
          ["parsed to tool_request schema - OK", "pass"],
          ["no capability token for that tool and agent pair - denied", "block"],
        ],
        agentReply: "Fraud model internals are never surfaced to a session - I can't share those.",
        verdictDetail: "BLOCKED - Layer 6 capability_token_denied",
      };
    }
    if (/CLM-\d+/.test(text.toUpperCase()) && !text.includes(p.claim)) {
      return {
        blockAt: 6,
        details: [
          ["NFKC normalised, 0 zero-width chars stripped", "pass"],
          ["0 static pattern matches", "pass"],
          ["adversarial score 0.3, below threshold - logged as signal only", "pass"],
          ["wrapped in untrusted-content delimiters", "pass"],
          ["valid claim_status intent, schema OK", "pass"],
          ["claim not owned by this session - 0 rows returned", "block"],
        ],
        agentReply: `I can only access ${p.claim} from this session - no visibility into other claims.`,
        verdictDetail: "BLOCKED - Layer 6 scoped_access_denial",
      };
    }
    if (/https?:\/\//.test(low)) {
      return {
        blockAt: 7,
        details: [
          ["NFKC normalised, 0 zero-width chars stripped", "pass"],
          ["0 static pattern matches", "pass"],
          ["adversarial score 0.35, below threshold - logged as signal only", "pass"],
          ["wrapped in untrusted-content delimiters", "pass"],
          ["valid intent, schema OK", "pass"],
          ["tool call scoped to own claim - OK", "pass"],
          ["URL not on allowlist, link removed before send", "block"],
        ],
        agentReply: "Noted - I stripped a link from my reply that was not on the approved domain list.",
        verdictDetail: "BLOCKED - Layer 7 egress_url_strip",
      };
    }
    return {
      blockAt: 0,
      details: [
        ["NFKC normalised, 0 zero-width chars stripped", "pass"],
        ["0 static pattern matches", "pass"],
        ["adversarial score 0.05, below threshold - clean", "pass"],
        ["wrapped in untrusted-content delimiters", "pass"],
        ["parsed cleanly, intent classified, schema OK", "pass"],
        ["tool calls scoped to own claim - OK", "pass"],
        ["no SECRET data, no PII, no external URLs - clear", "pass"],
      ],
      agentReply: `Thanks, ${first} - noted on ${p.claim}. Anything else I can help with?`,
      verdictDetail: "ALLOWED - all 7 layers clear",
    };
  }

  function classifyFile(file: File): RunSpec {
    const name = file.name.toLowerCase();
    const isImage = /\.(jpg|jpeg|png|gif|webp)$/.test(name) || file.type.startsWith("image/");
    const suspicious = /hidden|inject|overlay|sticker|malicious|exploit/.test(name);

    if (isImage) {
      if (suspicious) {
        return {
          blockAt: 5,
          details: [
            ["EXIF and XMP stripped, re-encoded — OCR located 1 text region, pixel-blurred to opaque block before the vision model looked", "pass"],
            ["0 static pattern matches on visible content", "pass"],
            ["adversarial score 0.4, below threshold — logged as signal only", "pass"],
            ["OCR text routed as separate untrusted stream, wrapped in delimiters", "pass"],
            ["OCR stream parsed — instruction_override_attempt anomaly — parser_schema_violation", "block"],
          ],
          agentReply: "I redacted an overlay on that image before anything could read it, and the extracted text didn't parse as legitimate evidence, so I've quarantined it.",
          verdictDetail: "BLOCKED — Layer 5 parser_schema_violation (image redacted successfully)",
        };
      }
      return {
        blockAt: 0,
        details: [
          ["EXIF and XMP stripped, re-encoded — OCR found 0 text regions", "pass"],
          ["0 static pattern matches on visible content", "pass"],
          ["adversarial score 0.05, below threshold — clean", "pass"],
          ["no OCR stream to parse — image-only", "pass"],
          ["damage-observation schema — OK", "pass"],
          [`attached to claim ${p.claim} as evidence — OK`, "pass"],
          ["no SECRET data, no PII, no external URLs — clear", "pass"],
        ],
        agentReply: `Got the photo — attached to ${p.claim}.`,
        verdictDetail: "ALLOWED — all 7 layers clear",
      };
    }

    if (suspicious) {
      return {
        blockAt: 1,
        details: [
          ["sandboxed parse (no network, read-only filesystem) — hidden-content scan found suspicious embedded content, rejected before parsing", "block"],
        ],
        agentReply: "That file got rejected before it was even parsed — hidden content was detected. Can you re-export it as a clean document?",
        verdictDetail: "BLOCKED — Layer 1 sandboxed_pdf_reject",
      };
    }
    return {
      blockAt: 0,
      details: [
        ["sandboxed parse (no network, read-only filesystem) — no JavaScript, no hidden layers, no active forms", "pass"],
        ["0 static pattern matches on extracted text", "pass"],
        ["adversarial score 0.04, below threshold — clean", "pass"],
        ["wrapped in untrusted-content delimiters", "pass"],
        ["parsed to document-fields schema — OK", "pass"],
        [`fields merged into claim ${p.claim} — OK`, "pass"],
        ["no SECRET data, no PII beyond policy scope, no external URLs — clear", "pass"],
      ],
      agentReply: `Thanks — that file parsed cleanly and is attached to ${p.claim}.`,
      verdictDetail: "ALLOWED — all 7 layers clear",
    };
  }

  function sendDraft() {
    const text = draft.trim();
    if (!text || running) return;
    run({ who: p.name, from: "user", isText: true, isFile: false, text }, classifyFreeText(text));
  }

  function onFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || running) return;
    run({ who: p.name, from: "user", isText: false, isFile: true, fileName: file.name }, classifyFile(file));
  }

  function newSession() {
    if (traceTimer.current) clearTimeout(traceTimer.current);
    if (thinkTimer.current) clearTimeout(thinkTimer.current);
    setMessages([{
      who: "Assistant",
      from: "agent",
      isText: true,
      isFile: false,
      text: `Hi ${first}, I can help file a new claim or answer questions about ${p.claim}. What’s going on?`,
      time: "now",
    }]);
    setDraft("");
    setRunning(false);
    setThinking(false);
    setLayerStates([]);
    setVerdict(null);
    setTraceId("—");
    setAuditRows([]);
    setCopied(false);
  }

  // Derived
  const categories = [
    { key: "text" as const, label: "Text" },
    { key: "pdf" as const, label: "Documents" },
    { key: "image" as const, label: "Images" },
  ];
  const filteredTemplates = templates.filter((t) => t.kind === activeCategory);
  const sendDisabled = running || !draft.trim();

  const sessionStatusColor = running ? "#3ECF8E" : "rgba(255,255,255,0.35)";
  const traceStatusColor = running ? "#3ECF8E" : verdict ? "rgba(255,255,255,0.5)" : "rgba(255,255,255,0.35)";
  const verdictColor = verdict ? (verdict.label === "BLOCKED" ? "#E5484D" : "#3ECF8E") : "rgba(255,255,255,0.35)";
  const verdictBg = verdict ? (verdict.label === "BLOCKED" ? "rgba(229,72,77,0.08)" : "rgba(62,207,142,0.06)") : "transparent";

  const layers = PG_LAYER_DEFS.map(([num, name, patterns], i) => {
    const ls = layerStates[i];
    const done = !!ls;
    const skipped = !!(verdict && !done);
    let status = "-";
    let statusColor = "rgba(255,255,255,0.25)";
    let detail = `pattern ${patterns}`;
    if (done) {
      detail = ls.detail;
      if (ls.kind === "pass") { status = "PASS"; statusColor = "rgba(255,255,255,0.55)"; }
      else if (ls.kind === "detect") { status = "DETECTED"; statusColor = "#E2A336"; }
      else { status = "BLOCKED"; statusColor = "#E5484D"; }
    } else if (skipped) {
      status = "NOT REACHED"; statusColor = "rgba(255,255,255,0.22)"; detail = "-";
    } else if (running && i === layerStates.length) {
      status = "RUNNING"; statusColor = "#3ECF8E";
    }
    const opacity = done || skipped || running ? 1 : 0.5;
    return { num, name, detail, status, statusColor, opacity };
  });

  return (
    <div style={{ height: "100vh", width: "100%", background: "#0A0B0C", display: "flex", flexDirection: "column", overflow: "hidden" }}>

      {/* NAV */}
      <nav style={{ flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 32px", height: "60px", background: "rgba(10,11,12,0.95)", borderBottom: "1px solid rgba(255,255,255,0.07)" }}>
        <Link href="/" style={{ display: "flex", alignItems: "center", gap: "10px", color: "rgba(255,255,255,0.95)", flexShrink: 0 }}>
          <span style={{ display: "inline-flex", width: "22px", height: "22px", border: "1.5px solid rgba(255,255,255,0.9)", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-geist-mono), monospace", fontSize: "11px", fontWeight: 600 }}>C</span>
          <span style={{ fontWeight: 600, fontSize: "15px", letterSpacing: "-0.01em" }}>Citadel</span>
        </Link>
        <div className="nav-links" style={{ display: "flex", alignItems: "center", gap: "26px" }}>
          {SITE_LINKS.map(({ label, href }) => (
            <Link key={href} href={href} style={{ fontSize: "13.5px", textDecoration: "none", color: pathname === href ? "rgba(255,255,255,0.95)" : "rgba(255,255,255,0.55)" }}>{label}</Link>
          ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "18px", flexShrink: 0 }}>
          <a
            href="https://github.com/Athish49/ProjectCitadel"
            target="_blank"
            rel="noopener noreferrer"
            className="link-dim"
            style={{ fontSize: "13.5px", fontFamily: "var(--font-geist-mono), monospace" }}
          >
            GitHub
          </a>
          <Link
            href="/architecture"
            className="btn-primary"
            style={{ fontSize: "13.5px", fontWeight: 600, padding: "8px 16px", borderRadius: "6px", whiteSpace: "nowrap" }}
          >
            Read the architecture
          </Link>
        </div>
      </nav>

      <div style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, minWidth: 0, overflow: "hidden" }}>

        {/* SESSION BAR */}
        <div style={{ borderBottom: "1px solid rgba(255,255,255,0.08)", background: "#0B0C0E", flexShrink: 0, minWidth: 0 }}>
          <div style={{ maxWidth: "1400px", margin: "0 auto", padding: "14px 32px", display: "flex", alignItems: "center", gap: "14px", minWidth: 0 }}>
            <span style={{ display: "inline-flex", width: "34px", height: "34px", borderRadius: "50%", background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.14)", alignItems: "center", justifyContent: "center", fontFamily: "var(--font-geist-mono), monospace", fontSize: "13px", fontWeight: 600, color: "rgba(255,255,255,0.85)", flexShrink: 0 }}>{p.initial}</span>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: "13.5px", fontWeight: 600, color: "rgba(255,255,255,0.92)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {p.name} <span style={{ fontWeight: 400, color: "rgba(255,255,255,0.4)" }}>· {p.vehicle}</span>
              </div>
              <div style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "11.5px", color: "rgba(255,255,255,0.42)", marginTop: "3px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                member {p.memberId} · policy {p.policy} · active claim {p.claim}
              </div>
            </div>
          </div>
        </div>

        {/* APP GRID */}
        <div data-app-grid="" style={{ flex: 1, minHeight: 0, minWidth: 0, display: "grid", gridTemplateColumns: "minmax(0, 1fr) 400px", gap: "20px", maxWidth: "1400px", width: "100%", margin: "0 auto", padding: "20px 32px", overflow: "hidden" }}>

          {/* LEFT: CHAT */}
          <div data-chat-panel="" style={{ border: "1px solid rgba(255,255,255,0.09)", background: "#0C0D0F", display: "flex", flexDirection: "column", minHeight: 0, minWidth: 0, height: "100%" }}>

            {/* chat header */}
            <div style={{ padding: "14px 18px", borderBottom: "1px solid rgba(255,255,255,0.07)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "10px", minWidth: 0 }}>
              <div style={{ minWidth: 0, overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>
                <span style={{ fontSize: "13.5px", fontWeight: 600, color: "rgba(255,255,255,0.9)" }}>Claims &amp; Service Assistant</span>
                <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "11px", color: "rgba(255,255,255,0.4)", marginLeft: "10px" }}>intent auto-classified by the quarantined parser</span>
              </div>
              {running ? (
                <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "11px", color: sessionStatusColor, flexShrink: 0 }}>
                  PROCESSING
                </span>
              ) : (
                <button
                  onClick={newSession}
                  className="btn-outline"
                  style={{ flexShrink: 0, background: "transparent", fontFamily: "var(--font-geist), sans-serif", fontSize: "12px", fontWeight: 500, padding: "5px 12px", borderRadius: "6px", cursor: "pointer", whiteSpace: "nowrap" }}
                >
                  New session
                </button>
              )}
            </div>

            {/* messages */}
            <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", overflowX: "hidden", minHeight: 0, padding: "18px 18px 6px", display: "flex", flexDirection: "column", gap: "14px" }}>
              {messages.map((m, idx) => {
                const isUser = m.from === "user";
                return (
                  <div key={idx} style={{ alignSelf: isUser ? "flex-end" : "flex-start", maxWidth: "78%", display: "flex", flexDirection: "column", gap: "4px", alignItems: isUser ? "flex-end" : "flex-start", minWidth: 0 }}>
                    <div style={{ fontSize: "13.5px", lineHeight: 1.55, padding: "11px 14px", borderRadius: isUser ? "10px 10px 2px 10px" : "10px 10px 10px 2px", background: isUser ? "rgba(255,255,255,0.95)" : "rgba(255,255,255,0.05)", color: isUser ? "#0A0B0C" : "rgba(255,255,255,0.85)", border: `1px solid ${isUser ? "transparent" : "rgba(255,255,255,0.08)"}`, minWidth: 0 }}>
                      {m.isFile && (
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", fontFamily: "var(--font-geist-mono), monospace", fontSize: "12px" }}>
                          <span style={{ opacity: 0.6, border: "1px solid rgba(255,255,255,0.3)", borderRadius: "3px", padding: "1px 5px", fontSize: "10px" }}>FILE</span>
                          <span>{m.fileName}</span>
                        </div>
                      )}
                      {m.isText && <span style={{ wordBreak: "break-word", overflowWrap: "anywhere" }}>{m.text}</span>}
                    </div>
                    <div style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "10.5px", color: "rgba(255,255,255,0.3)", padding: "0 2px" }}>{m.who} · {m.time}</div>
                  </div>
                );
              })}

              {/* thinking dots */}
              {thinking && (
                <div style={{ alignSelf: "flex-start", maxWidth: "78%" }}>
                  <div style={{ display: "inline-flex", gap: "4px", background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)", padding: "10px 14px", borderRadius: "10px 10px 10px 2px" }}>
                    {[0, 0.15, 0.3].map((delay, i) => (
                      <span key={i} style={{ display: "inline-block", width: "5px", height: "5px", borderRadius: "50%", background: "rgba(255,255,255,0.5)", animation: `citadel-pulse 1s ease-in-out ${delay}s infinite` }} />
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* template chips */}
            <div style={{ borderTop: "1px solid rgba(255,255,255,0.07)", padding: "12px 18px 4px", minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "9px", gap: "10px" }}>
                <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "10.5px", letterSpacing: "0.08em", color: "rgba(255,255,255,0.35)" }}>TRY A TEMPLATE</span>
                <div style={{ display: "flex", gap: "6px" }}>
                  {categories.map((cat) => {
                    const active = cat.key === activeCategory;
                    return (
                      <button
                        key={cat.key}
                        onClick={() => setActiveCategory(cat.key)}
                        style={{ background: active ? "rgba(255,255,255,0.95)" : "transparent", color: active ? "#0A0B0C" : "rgba(255,255,255,0.55)", border: `1px solid ${active ? "transparent" : "rgba(255,255,255,0.14)"}`, fontFamily: "var(--font-geist), sans-serif", fontSize: "11.5px", fontWeight: 600, padding: "5px 12px", borderRadius: "999px", cursor: "pointer", transition: "all 0.15s" }}
                      >
                        {cat.label}
                      </button>
                    );
                  })}
                </div>
              </div>
              <div style={{ display: "flex", gap: "8px", overflowX: "auto", overflowY: "hidden", paddingBottom: "10px", minWidth: 0 }}>
                {filteredTemplates.map((t) => {
                  const isAttack = t.tax !== "benign";
                  return (
                    <button
                      key={t.id}
                      onClick={() => runTemplate(t)}
                      disabled={running}
                      style={{ display: "inline-flex", alignItems: "center", gap: "7px", whiteSpace: "nowrap", flexShrink: 0, background: "transparent", border: "1px solid rgba(255,255,255,0.14)", color: "rgba(255,255,255,0.75)", fontFamily: "var(--font-geist), sans-serif", fontSize: "12px", fontWeight: 500, padding: "8px 13px", borderRadius: "999px", cursor: running ? "not-allowed" : "pointer", opacity: running ? 0.5 : 1, transition: "border-color 0.15s" }}
                      onMouseEnter={(e) => { if (!running) (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.4)"; }}
                      onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.14)"; }}
                    >
                      <span style={{ display: "inline-block", width: "6px", height: "6px", borderRadius: "50%", background: isAttack ? "#E5484D" : "#3ECF8E", flexShrink: 0 }} />
                      <span>{t.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* input */}
            <div style={{ padding: "6px 18px 18px", display: "flex", gap: "10px", alignItems: "flex-end", minWidth: 0 }}>
              <label
                htmlFor="pg-file-input"
                title="Attach a document or image"
                style={{ flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", width: "40px", height: "40px", background: "#08090A", border: "1px solid rgba(255,255,255,0.14)", color: "rgba(255,255,255,0.6)", borderRadius: "8px", cursor: "pointer", transition: "border-color 0.15s, color 0.15s" }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.4)"; (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.9)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.14)"; (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.6)"; }}
              >
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48" />
                </svg>
              </label>
              <input id="pg-file-input" type="file" accept=".pdf,image/*" onChange={onFileSelected} style={{ display: "none" }} />
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendDraft(); } }}
                rows={1}
                placeholder={`Type as ${p.name} — a claim update, a question, or try to break it…`}
                style={{ flex: 1, minWidth: 0, resize: "none", background: "#08090A", border: "1px solid rgba(255,255,255,0.12)", color: "rgba(255,255,255,0.85)", fontSize: "13px", lineHeight: 1.5, padding: "11px 13px", borderRadius: "8px", fontFamily: "inherit", outline: "none" }}
              />
              <button
                onClick={sendDraft}
                disabled={sendDisabled}
                className="btn-primary"
                style={{ flexShrink: 0, border: "none", fontFamily: "var(--font-geist), sans-serif", fontSize: "13px", fontWeight: 600, padding: "11px 18px", borderRadius: "8px", cursor: sendDisabled ? "not-allowed" : "pointer", opacity: sendDisabled ? 0.5 : 1, whiteSpace: "nowrap" }}
              >
                Send
              </button>
            </div>
          </div>

          {/* RIGHT: TRACE */}
          <div data-trace-panel="" style={{ border: "1px solid rgba(255,255,255,0.09)", background: "#0C0D0F", display: "flex", flexDirection: "column", minHeight: 0, minWidth: 0, height: "100%" }}>

            {/* trace header */}
            <div style={{ padding: "14px 18px", borderBottom: "1px solid rgba(255,255,255,0.07)", minWidth: 0 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "8px", minWidth: 0 }}>
                <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "11px", letterSpacing: "0.08em", color: "rgba(255,255,255,0.4)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  /sse/playground/{traceId}
                </span>
                <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "11px", color: traceStatusColor, flexShrink: 0 }}>
                  {running ? "STREAMING" : verdict ? "COMPLETE" : "IDLE"}
                </span>
              </div>
            </div>

            <div style={{ overflowY: "auto", overflowX: "hidden", flex: 1, minHeight: 0 }}>
              {/* layers */}
              {layers.map((ly) => (
                <div key={ly.num} style={{ padding: "12px 18px", borderBottom: "1px solid rgba(255,255,255,0.05)", opacity: ly.opacity, transition: "opacity 0.3s ease" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: "10px" }}>
                    <span style={{ display: "flex", alignItems: "baseline", gap: "8px", minWidth: 0 }}>
                      <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "11px", color: "rgba(255,255,255,0.35)" }}>{ly.num}</span>
                      <span style={{ fontSize: "13px", fontWeight: 500, color: "rgba(255,255,255,0.88)" }}>{ly.name}</span>
                    </span>
                    <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "10.5px", letterSpacing: "0.04em", color: ly.statusColor, flexShrink: 0 }}>{ly.status}</span>
                  </div>
                  <div style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "11px", color: "rgba(255,255,255,0.46)", lineHeight: 1.5, marginTop: "5px", wordBreak: "break-word", overflowWrap: "anywhere" }}>{ly.detail}</div>
                </div>
              ))}

              {/* audit rows */}
              <div style={{ padding: "12px 18px 4px", marginTop: "4px" }}>
                <div style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "10px", letterSpacing: "0.08em", color: "rgba(255,255,255,0.3)" }}>AUDIT ROWS — THIS TRACE</div>
              </div>
              {auditRows.map((a, i) => (
                <div key={i} style={{ padding: "8px 18px", display: "flex", justifyContent: "space-between", gap: "10px", alignItems: "baseline" }}>
                  <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "10.5px", color: a.color }}>{a.tag}</span>
                  <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "10px", color: "rgba(255,255,255,0.28)", whiteSpace: "nowrap" }}>+{a.elapsed}</span>
                </div>
              ))}
            </div>

            {/* verdict */}
            <div style={{ padding: "16px 18px", background: verdictBg, borderTop: "1px solid rgba(255,255,255,0.07)", transition: "background 0.4s ease", minWidth: 0 }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "12.5px", fontWeight: 600, letterSpacing: "0.05em", color: verdictColor }}>{verdict?.label ?? ""}</span>
                <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "11px", color: "rgba(255,255,255,0.5)" }}>
                  {verdict ? verdict.detail : running ? "running..." : "Select a template or type a message to start a trace."}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "8px", gap: "10px" }}>
                <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "10.5px", color: "rgba(255,255,255,0.35)" }}>{verdict?.audits ?? ""}</span>
                {verdict && (
                  <button
                    onClick={() => { setCopied(true); setTimeout(() => setCopied(false), 1600); }}
                    style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "11px", color: "rgba(255,255,255,0.6)", cursor: "pointer", whiteSpace: "nowrap", background: "none", border: "none", padding: 0, transition: "color 0.15s" }}
                    onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,1)"; }}
                    onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "rgba(255,255,255,0.6)"; }}
                  >
                    {copied ? "Copied" : "Copy replay link"}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
