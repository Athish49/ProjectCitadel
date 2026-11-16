"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Nav } from "@/components/layout/nav";
import { Footer } from "@/components/layout/footer";
import { StateTrace } from "@/components/formal/state-trace";
import { ReachabilityMatrix } from "@/components/formal/reachability-matrix";
import { useRunCheck, RunCheckPanel } from "@/components/formal/run-check";
import {
  HERO_STATS, INVARIANTS, INVARIANT_NAMES,
  METHOD_NODES, METHOD_ARROW_LABELS, METHOD_LOOP_CAPTION,
  SCOPE_PROVEN, SCOPE_OUTSIDE,
} from "@/lib/data/formal";

// This page's design uses the larger type scale than the shared default —
// applied as inline overrides on top of the shared .eb/.sec/.h2 classes,
// per the page brief, rather than editing globals.css.
const ebBig = { color: "rgba(255,255,255,.58)" } as const;
const secBig = { padding: "clamp(80px,9vw,136px) 32px 0" } as const;
const h2Big = { fontSize: "clamp(28px,3.4vw,44px)" } as const;

export function FormalPage() {
  const { data, loading, error, run } = useRunCheck();

  useEffect(() => {
    const root = document.querySelector('[data-page="formal"]');
    const reduce = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!root || reduce || typeof IntersectionObserver === "undefined") return;
    root.setAttribute("data-anim", "on");
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.setAttribute("data-in", "1");
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.03 });
    document.querySelectorAll("[data-rv]").forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  const passCount = data ? Object.values(data.invariant_results).filter(Boolean).length : null;
  const total = INVARIANT_NAMES.length;

  return (
    <div data-page="formal" style={{ background: "#0a0b0c", color: "rgba(255,255,255,.95)", fontFamily: "var(--font-geist), 'Helvetica Neue', sans-serif", fontSize: "15px", lineHeight: 1.6, minHeight: "100vh" }}>
      <Nav />

      <main>
        {/* ── Hero ── */}
        <section style={{ maxWidth: "1264px", margin: "0 auto", padding: "clamp(64px,9vw,120px) 32px 0" }}>
          <div data-rv className="eb" style={ebBig}>Formal verification</div>
          <h1 data-rv style={{ margin: "22px 0 0", fontSize: "clamp(40px,6.4vw,84px)", lineHeight: 1, letterSpacing: "-.04em", fontWeight: 600, maxWidth: "940px", transitionDelay: "80ms" }}>
            Not just tested. Checked exhaustively.
          </h1>
          <p data-rv style={{ margin: "26px 0 0", maxWidth: "600px", fontSize: "clamp(17px,1.5vw,19px)", lineHeight: 1.5, color: "rgba(255,255,255,.7)", transitionDelay: "160ms" }}>
            The claim workflow is specified in TLA+ and model-checked in every state it can ever reach.
          </p>

          <div data-rv style={{ marginTop: "56px", display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(180px,100%),1fr))", gap: "1px", background: "rgba(255,255,255,.08)", border: "1px solid rgba(255,255,255,.08)", transitionDelay: "240ms" }}>
            {HERO_STATS.map((st) => {
              let n = st.n;
              let color = st.color;
              if (st.live === "visited" && data) n = data.visited.toLocaleString("en-US");
              if (st.live === "invariants" && passCount !== null) {
                n = `${passCount} / ${total}`;
                color = passCount === total ? "#3ECF8E" : "#E5484D";
              }
              return (
                <div key={st.label} className="cell" style={{ padding: "20px 20px 22px" }}>
                  <div className="mono" style={{ fontSize: "28px", lineHeight: 1, fontWeight: 500, color: color ?? "inherit" }}>{n}</div>
                  <div style={{ marginTop: "10px", fontSize: "13px", color: "rgba(255,255,255,.62)" }}>{st.label}</div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ── 01 Method ── */}
        <section className="sec" style={secBig}>
          <div data-rv>
            <div className="eb" style={ebBig}>01 — Method</div>
            <h2 className="h2" style={h2Big}>Code, spec and proof form a closed loop.</h2>
            <p className="lead">The spec is derived from the code, the checker proves the spec, and conformance tests tie the proof back to the code.</p>
          </div>

          <div data-rv className="panel" style={{ marginTop: "44px", padding: "28px 22px" }}>
            <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "center", gap: "0", overflowX: "auto" }}>
              {METHOD_NODES.map((n, i) => (
                <div key={n.title} style={{ display: "flex", alignItems: "center" }}>
                  <div
                    style={{
                      width: "216px", minHeight: "88px", boxSizing: "border-box", padding: "8px 14px",
                      display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center",
                      background: "#101114",
                      border: `1px solid ${n.accent ? "rgba(62,207,142,.45)" : "rgba(255,255,255,.14)"}`,
                      borderRadius: "6px", color: "rgba(255,255,255,.95)", fontSize: "14px", lineHeight: 1.3,
                    }}
                  >
                    <span>
                      <b style={{ fontWeight: 500, color: n.accent ? "#3ecf8e" : "inherit" }}>{n.title}</b>
                      <br />
                      <span style={{ fontSize: "12.5px", color: "rgba(255,255,255,.62)" }}>{n.sub}</span>
                    </span>
                  </div>
                  {i < METHOD_NODES.length - 1 && (
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: "96px", flexShrink: 0 }}>
                      <span style={{ fontSize: "13px", color: "rgba(255,255,255,.6)" }}>{METHOD_ARROW_LABELS[i]}</span>
                      <span style={{ color: "rgba(255,255,255,.38)", fontSize: "18px", lineHeight: 1 }}>→</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
            <div style={{ marginTop: "22px", paddingTop: "18px", borderTop: "1px dashed rgba(62,207,142,.4)", display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
              <span style={{ color: "#7fdcb0", fontSize: "13px" }}>↩</span>
              <span style={{ fontSize: "13px", color: "#7fdcb0" }}>{METHOD_LOOP_CAPTION}</span>
            </div>
          </div>
        </section>

        {/* ── 02 State machine ── */}
        <section className="sec" style={secBig}>
          <div data-rv>
            <div className="eb" style={ebBig}>02 — The state machine</div>
            <h2 className="h2" style={h2Big}>Nine stages. Eleven ways to move.</h2>
            <p className="lead">Columns are ranks. Every arrow points to a higher rank, so a claim can only move forward. Trace a claim to see its guards.</p>
          </div>
          <div data-rv>
            <StateTrace />
          </div>
        </section>

        {/* ── 03 Invariants ── */}
        <section className="sec" style={secBig}>
          <div data-rv>
            <div className="eb" style={ebBig}>03 — Invariants</div>
            <h2 className="h2" style={h2Big}>Seven properties that can never break.</h2>
            <p className="lead">Six safety properties and one liveness property, each shown as a move the system allows and one it never will.</p>
          </div>

          <div data-rv style={{ marginTop: "44px", display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(280px,100%),1fr))", gap: "1px", background: "rgba(255,255,255,.08)", border: "1px solid rgba(255,255,255,.08)" }}>
            {INVARIANTS.map((iv) => {
              const result = data?.invariant_results[iv.name];
              const statusLabel = error ? "UNKNOWN" : result === undefined ? (loading ? "CHECKING…" : "NOT YET RUN") : result ? "HOLDS" : "VIOLATED";
              const statusColor = error ? "rgba(255,255,255,.4)" : result === undefined ? "rgba(255,255,255,.5)" : result ? "#3ecf8e" : "#f0787c";
              return (
                <div key={iv.name} className="cell" style={{ padding: "22px 22px 24px", display: "flex", flexDirection: "column", gap: "12px" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: "12px" }}>
                    <span className="mono" style={{ fontSize: "11px", letterSpacing: ".1em", color: "rgba(255,255,255,.58)" }}>{iv.kind}</span>
                    <span className="mono" style={{ fontSize: "11px", letterSpacing: ".1em", color: statusColor }}>{statusLabel}</span>
                  </div>
                  <div style={{ fontSize: "17px", fontWeight: 500 }}>{iv.name}</div>
                  <p style={{ margin: 0, fontSize: "14px", color: "rgba(255,255,255,.72)", minHeight: "44px" }}>{iv.plain}</p>
                  <div className="mono" style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "12px" }}>
                    <div style={{ display: "flex", gap: "10px", alignItems: "center", padding: "8px 10px", border: "1px solid rgba(62,207,142,.35)", borderRadius: "4px" }}>
                      <span style={{ color: "#3ecf8e", flex: "0 0 52px" }}>allowed</span><span>{iv.allowed}</span>
                    </div>
                    <div style={{ display: "flex", gap: "10px", alignItems: "center", padding: "8px 10px", border: "1px solid rgba(240,120,124,.4)", borderRadius: "4px" }}>
                      <span style={{ color: "#f0787c", flex: "0 0 52px" }}>never</span>
                      <span style={{ color: "rgba(255,255,255,.72)", textDecoration: "line-through", textDecorationColor: "rgba(240,120,124,.7)" }}>{iv.never}</span>
                    </div>
                  </div>
                  <div className="mono" style={{ marginTop: "auto", fontSize: "11px", color: "rgba(255,255,255,.55)" }}>{iv.standards.join(" · ")}</div>
                </div>
              );
            })}
            <div className="cell" style={{ padding: "22px", display: "flex", flexDirection: "column", justifyContent: "flex-end", gap: "10px" }}>
              <div className="mono" style={{ fontSize: "40px", lineHeight: 1, fontWeight: 500, color: error ? "rgba(255,255,255,.4)" : data && !data.all_hold ? "#E5484D" : "#3ecf8e" }}>
                {error ? "—" : data ? data.violations.length : loading ? "…" : "0"}
              </div>
              <div style={{ fontSize: "14px", color: "rgba(255,255,255,.72)" }}>
                {error
                  ? "violations unknown — backend unreachable."
                  : data
                  ? `violation${data.violations.length === 1 ? "" : "s"} found across ${data.visited.toLocaleString("en-US")} states, checked in ${data.elapsed_ms} ms.`
                  : "violations found — running the checker…"}
              </div>
            </div>
          </div>
        </section>

        {/* ── 04 Exhaustive search (live) ── */}
        <section className="sec" style={secBig}>
          <div data-rv>
            <div className="eb" style={ebBig}>04 — Exhaustive search</div>
            <h2 className="h2" style={h2Big}>Every reachable state, not a sample.</h2>
            <p className="lead">The checker starts from a new claim and expands outward until nothing new appears — run live against the real backend.</p>
          </div>
          <div data-rv style={{ marginTop: "44px" }}>
            <RunCheckPanel data={data} loading={loading} error={error} onRerun={run} />
          </div>
        </section>

        {/* ── 05 Conformance ── */}
        <section className="sec" style={secBig}>
          <div data-rv>
            <div className="eb" style={ebBig}>05 — Conformance</div>
            <h2 className="h2" style={h2Big}>81 stage pairs. 11 accepted, 70 refused.</h2>
            <p className="lead">Every possible jump between two stages was fired at the running code. It accepted exactly the eleven the spec allows.</p>
          </div>
          <div data-rv>
            <ReachabilityMatrix />
          </div>
        </section>

        {/* ── 06 Scope ── */}
        <section className="sec" style={secBig}>
          <div data-rv>
            <div className="eb" style={ebBig}>06 — Scope</div>
            <h2 className="h2" style={h2Big}>What the proof covers, and what it does not.</h2>
          </div>
          <div data-rv style={{ marginTop: "44px", display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(360px,100%),1fr))", gap: "1px", background: "rgba(255,255,255,.08)", border: "1px solid rgba(255,255,255,.08)" }}>
            <div className="cell" style={{ background: "#0c0d0f" }}>
              <div className="mono" style={{ padding: "14px 20px", fontSize: "11px", letterSpacing: ".1em", textTransform: "uppercase", color: "#3ecf8e" }}>Proven</div>
              {SCOPE_PROVEN.map((s) => (
                <div key={s} style={{ padding: "13px 20px", borderTop: "1px solid rgba(255,255,255,.06)", fontSize: "14.5px", color: "rgba(255,255,255,.82)" }}>{s}</div>
              ))}
            </div>
            <div className="cell" style={{ background: "#0c0d0f" }}>
              <div className="mono" style={{ padding: "14px 20px", fontSize: "11px", letterSpacing: ".1em", textTransform: "uppercase", color: "#e2a336" }}>Outside the proof</div>
              {SCOPE_OUTSIDE.map((s) => (
                <div key={s} style={{ padding: "13px 20px", borderTop: "1px solid rgba(255,255,255,.06)", fontSize: "14.5px", color: "rgba(255,255,255,.82)" }}>{s}</div>
              ))}
            </div>
          </div>
          <p data-rv style={{ margin: "24px 0 0", fontSize: "14px", color: "rgba(255,255,255,.62)" }}>
            Full specification and checker: <a href="https://github.com/Athish49/ProjectCitadel" className="link-dim" target="_blank" rel="noopener noreferrer">backend/formal on GitHub</a>
          </p>
        </section>

        {/* ── Final CTA ── */}
        <section style={{ marginTop: "clamp(88px,10vw,140px)", borderTop: "1px solid rgba(255,255,255,.08)" }}>
          <div data-rv style={{ maxWidth: "1264px", margin: "0 auto", padding: "clamp(72px,9vw,120px) 32px", display: "flex", flexWrap: "wrap", alignItems: "flex-end", justifyContent: "space-between", gap: "32px 64px" }}>
            <div style={{ maxWidth: "680px" }}>
              <h2 style={{ margin: 0, fontSize: "clamp(30px,4.2vw,54px)", lineHeight: 1.04, letterSpacing: "-.035em", fontWeight: 600 }}>
                The proof covers the state machine. The rest is runtime.
              </h2>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "12px" }}>
              <Link className="btn btn-p" href="/architecture">See the architecture</Link>
              <Link className="btn btn-g" href="/playground">Launch the playground</Link>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
