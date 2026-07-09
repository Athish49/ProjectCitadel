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
  type TemplateSpec,
} from "@/lib/data/playground";
import { usePlaygroundStream } from "@/lib/hooks/use-playground-stream";
import type { AttackComposerTab } from "@/lib/types/playground";

interface Message {
  who: string;
  from: "user" | "agent";
  isText: boolean;
  isFile: boolean;
  text?: string;
  fileName?: string;
  time: string;
}

const PERSONA: Persona = PERSONAS[0];

export function PlaygroundApp() {
  const p = PERSONA;
  const templates = makeTemplates(p);
  const first = p.name.split(" ")[0];
  const pathname = usePathname();

  const { trace, isStreaming, error, submit } = usePlaygroundStream();

  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [thinking, setThinking] = useState(false);
  const [copied, setCopied] = useState(false);
  const [activeCategory, setActiveCategory] = useState<"text" | "pdf" | "image">("text");

  const scrollRef = useRef<HTMLDivElement>(null);
  const thinkTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Track which verdicts have been surfaced as agent replies to avoid duplicates
  const verdictKeyRef = useRef<string | null>(null);

  useEffect(() => {
    setMessages([{
      who: "Assistant",
      from: "agent",
      isText: true,
      isFile: false,
      text: `Hi ${first}, I can help file a new claim or answer questions about ${p.claim}. What's going on?`,
      time: "now",
    }]);
    return () => { if (thinkTimer.current) clearTimeout(thinkTimer.current); };
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, thinking]);

  // When a verdict arrives, add the agent reply to the chat
  useEffect(() => {
    if (!trace?.verdict || !trace?.traceId) return;
    const key = `${trace.traceId}:${trace.verdict.outcome}`;
    if (verdictKeyRef.current === key) return;
    verdictKeyRef.current = key;
    if (thinkTimer.current) clearTimeout(thinkTimer.current);
    setThinking(true);
    thinkTimer.current = setTimeout(() => {
      setThinking(false);
      setMessages((prev) => [...prev, {
        who: "Assistant",
        from: "agent",
        isText: true,
        isFile: false,
        text: trace.verdict!.summary,
        time: "now",
      }]);
    }, 650);
  }, [trace?.verdict, trace?.traceId]);

  function pushUserMessage(msg: Omit<Message, "time">) {
    setMessages((prev) => [...prev, { ...msg, time: "now" }]);
    verdictKeyRef.current = null; // allow next verdict
    if (thinkTimer.current) clearTimeout(thinkTimer.current);
    setThinking(false);
  }

  function sendDraft() {
    const text = draft.trim();
    if (!text || isStreaming) return;
    pushUserMessage({ who: p.name, from: "user", isText: true, isFile: false, text });
    setDraft("");
    submit(text, "chat", "intake", "live");
  }

  function runTemplate(spec: TemplateSpec) {
    if (isStreaming) return;
    const bubble: Omit<Message, "time"> =
      spec.kind === "text"
        ? { who: p.name, from: "user", isText: true, isFile: false, text: spec.userText }
        : { who: p.name, from: "user", isText: false, isFile: true, fileName: spec.fileName };
    pushUserMessage(bubble);
    const tab: AttackComposerTab = spec.kind === "text" ? "chat" : spec.kind;
    const payload = spec.kind === "text" ? spec.userText : (spec.userText || spec.fileName || "file");
    submit(payload, tab, "intake", "live");
  }

  function onFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file || isStreaming) return;
    const tab: AttackComposerTab = file.type.startsWith("image/") ? "image" : "pdf";
    pushUserMessage({ who: p.name, from: "user", isText: false, isFile: true, fileName: file.name });
    submit(file.name, tab, "intake", "live");
  }

  function newSession() {
    if (thinkTimer.current) clearTimeout(thinkTimer.current);
    verdictKeyRef.current = null;
    setMessages([{
      who: "Assistant",
      from: "agent",
      isText: true,
      isFile: false,
      text: `Hi ${first}, I can help file a new claim or answer questions about ${p.claim}. What's going on?`,
      time: "now",
    }]);
    setDraft("");
    setThinking(false);
    setCopied(false);
  }

  // ── Derived display state ────────────────────────────────────────────────────

  const traceId    = trace?.traceId ?? "—";
  const verdict    = trace?.verdict ?? null;
  const running    = isStreaming;

  const categories = [
    { key: "text" as const, label: "Text" },
    { key: "pdf" as const, label: "Documents" },
    { key: "image" as const, label: "Images" },
  ];
  const filteredTemplates = templates.filter((t) => t.kind === activeCategory);
  const sendDisabled = running || !draft.trim();

  const sessionStatusColor = running ? "#3ECF8E" : "rgba(255,255,255,0.35)";
  const traceStatusColor   = running ? "#3ECF8E" : verdict ? "rgba(255,255,255,0.5)" : "rgba(255,255,255,0.35)";
  const verdictColor       = verdict
    ? verdict.outcome === "BLOCKED" ? "#E5484D"
      : verdict.outcome === "BREACH" ? "#E5484D"
      : "#3ECF8E"
    : "rgba(255,255,255,0.35)";
  const verdictBg = verdict
    ? (verdict.outcome === "BLOCKED" || verdict.outcome === "BREACH")
      ? "rgba(229,72,77,0.08)"
      : "rgba(62,207,142,0.06)"
    : "transparent";
  const verdictLabel = verdict
    ? verdict.outcome === "CLEAN" ? "ALLOWED"
      : verdict.outcome === "PARTIAL" ? "PARTIAL"
      : verdict.outcome
    : "";

  // Map real trace layers → display format
  const layers = PG_LAYER_DEFS.map(([num, name, patterns], i) => {
    const rl = trace?.layers[i];
    let status = "-";
    let statusColor = "rgba(255,255,255,0.25)";
    let detail = `pattern ${patterns}`;

    if (rl) {
      if (rl.status === "passed") {
        status = "PASS"; statusColor = "rgba(255,255,255,0.55)";
        detail = rl.events[0]?.message ?? (rl.durationMs != null ? `${rl.durationMs}ms` : "passed");
      } else if (rl.status === "blocked") {
        status = "BLOCKED"; statusColor = "#E5484D";
        detail = rl.events[0]?.message ?? "blocked";
      } else if (rl.status === "partial") {
        status = "DETECTED"; statusColor = "#E2A336";
        detail = rl.events[0]?.message ?? "detected";
      } else if (rl.status === "running") {
        status = "RUNNING"; statusColor = "#3ECF8E";
      } else if (rl.status === "pending" && verdict) {
        status = "NOT REACHED"; statusColor = "rgba(255,255,255,0.22)"; detail = "-";
      }
    }

    const opacity = rl && rl.status !== "pending" ? 1 : 0.5;
    return { num, name, detail, status, statusColor, opacity };
  });

  // Derive audit rows from completed layers
  const auditRows = (trace?.layers ?? [])
    .filter((l) => l.status !== "pending" && l.status !== "running")
    .map((l) => ({
      tag: l.status === "blocked" ? "defense_fired"
        : l.status === "partial" ? "pattern_detected"
        : "layer_pass",
      color: l.status === "blocked" ? "#E5484D"
        : l.status === "partial" ? "#E2A336"
        : "#3ECF8E",
      elapsed: l.durationMs != null ? `${(l.durationMs / 1000).toFixed(2)}s` : "—",
    }));

  const verdictAudits = auditRows.length > 0
    ? `${auditRows.length} audit rows written, chain intact`
    : "";

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

        {/* Error banner */}
        {error && (
          <div style={{ flexShrink: 0, padding: "8px 32px", borderBottom: "1px solid rgba(229,72,77,0.4)", background: "rgba(229,72,77,0.08)", fontFamily: "var(--font-geist-mono), monospace", fontSize: "12px", color: "#E5484D" }}>
            {error}
          </div>
        )}

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
                <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "12.5px", fontWeight: 600, letterSpacing: "0.05em", color: verdictColor }}>{verdictLabel}</span>
                <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "11px", color: "rgba(255,255,255,0.5)" }}>
                  {verdict
                    ? verdict.blockedByLayer
                      ? `blocked at ${verdict.blockedByLayer}`
                      : verdict.outcome === "CLEAN" ? "all layers passed" : verdict.outcome.toLowerCase()
                    : running
                    ? "running..."
                    : "Select a template or type a message to start a trace."}
                </span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "8px", gap: "10px" }}>
                <span style={{ fontFamily: "var(--font-geist-mono), monospace", fontSize: "10.5px", color: "rgba(255,255,255,0.35)" }}>{verdictAudits}</span>
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
