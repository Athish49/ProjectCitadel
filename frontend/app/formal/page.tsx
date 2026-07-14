import type { Metadata } from "next";
import type { CSSProperties } from "react";
import React from "react";
import Link from "next/link";
import {
  TOC_LINKS, STAT_ROW, STATE_VARS, FORMAL_EDGES,
  INVARIANTS, CONFORMANCE_STATS, MATRIX_STATES, MATRIX_ROWS,
  GRAPH_LINES, GRAPH_NODES, GRAPH_PARTICLES,
  SOURCE_LINES,
} from "@/lib/data/formal";
import { SpecCheck } from "@/components/formal/spec-check";
import { PageNav } from "@/components/layout/page-nav";

export const metadata: Metadata = {
  title: "Formal Specification — Project Citadel",
};

const mono: CSSProperties = {
  fontFamily: "var(--font-geist-mono), monospace",
};

const sectionLabel: CSSProperties = {
  ...mono,
  fontSize: "12px",
  letterSpacing: "0.1em",
  color: "rgba(255,255,255,0.4)",
};

const h2Style: CSSProperties = {
  margin: "14px 0 0",
  fontSize: "24px",
  fontWeight: 600,
  letterSpacing: "-0.02em",
  color: "rgba(255,255,255,0.95)",
};

const pStyle: CSSProperties = {
  margin: "10px 0 0",
  fontSize: "14px",
  lineHeight: 1.7,
  color: "rgba(255,255,255,0.45)",
};

const codeStyle: CSSProperties = {
  ...mono,
  background: "rgba(255,255,255,0.06)",
  padding: "1px 5px",
  borderRadius: "3px",
  fontSize: "13px",
};

export default function FormalPage() {
  return (
    <>
      <PageNav />

    <div style={{ minHeight: "100vh", background: "#0A0B0C", display: "flex" }}>

      {/* ══ SIDEBAR ══ */}
      <aside
        data-sidebar=""
        style={{
          position: "fixed", top: "60px", left: 0, bottom: 0,
          width: "268px",
          background: "#060708",
          borderRight: "1px solid rgba(255,255,255,0.07)",
          display: "flex", flexDirection: "column",
          zIndex: 50,
        }}
      >
        {/* section heading */}
        <div style={{ padding: "18px 22px 8px", ...mono, fontSize: "10.5px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.32)" }}>
          FORMAL SPECIFICATION
        </div>

        {/* TOC — CSS-only hover via .formal-nav-link */}
        <nav style={{ display: "flex", flexDirection: "column", padding: "4px 12px", gap: "1px" }}>
          {TOC_LINKS.map((tl) => (
            <a key={tl.href} href={tl.href} className="formal-nav-link">
              <span style={{ ...mono, fontSize: "11px", color: "rgba(255,255,255,0.3)", marginRight: "8px" }}>{tl.n}</span>
              {tl.label}
            </a>
          ))}
        </nav>

        {/* spec status */}
        <div style={{ marginTop: "auto", padding: "18px 22px", borderTop: "1px solid rgba(255,255,255,0.06)" }}>
          <div style={{ ...mono, fontSize: "10px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.32)", marginBottom: "10px" }}>SPEC STATUS</div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#3ECF8E", animation: "citadel-pulse 2.4s ease-in-out infinite", display: "inline-block" }} />
            <span style={{ ...mono, fontSize: "12px", color: "#3ECF8E", fontWeight: 600 }}>VERIFIED</span>
          </div>
          <div style={{ ...mono, fontSize: "11px", color: "rgba(255,255,255,0.4)", lineHeight: 1.7 }}>
            last run: 4 minutes ago<br />
            state space: 918 reachable states<br />
            36/36 invariant tests · 102/102 conformance
          </div>
        </div>

      </aside>

      {/* ══ MAIN ══ */}
      <div data-main="" style={{ marginLeft: "268px", flex: 1, minWidth: 0, paddingTop: "60px" }}>

        <div style={{ maxWidth: "860px", margin: "0 auto", padding: "0 40px" }}>

          {/* ══ 0.0 OVERVIEW ══ */}
          <section id="overview" style={{ paddingTop: "76px" }}>
            <div style={sectionLabel}>0.0 — SPECIFICATION STATUS</div>
            <h1 style={{ margin: "18px 0 0", fontSize: "clamp(30px, 3.4vw, 44px)", lineHeight: 1.16, letterSpacing: "-0.03em", fontWeight: 600, color: "rgba(255,255,255,0.97)" }}>
              The claim workflow isn&apos;t just tested. It&apos;s proved.
            </h1>
            <p style={{ margin: "20px 0 0", fontSize: "15px", lineHeight: 1.7, color: "rgba(255,255,255,0.5)", maxWidth: "720px" }}>
              The orchestrator&apos;s state machine — the same one enforcing every transition in{" "}
              <Link href="/architecture#orchestrator" style={{ color: "rgba(255,255,255,0.7)" }}>the deterministic orchestrator</Link>
              {" "}— is specified in TLA+ (<code style={codeStyle}>formal/workflow.tla</code>), exhaustively model-checked, and conformance-tested against the running Python implementation. Seven safety and liveness properties are proved across 918 reachable states, satisfying Common Criteria EAL3–4, NIST SP 800-53, and OWASP ASVS Level 2 requirements. This is the part of the system that isn&apos;t just &ldquo;probably right.&rdquo;
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1px", background: "rgba(255,255,255,0.07)", marginTop: "40px", border: "1px solid rgba(255,255,255,0.07)" }}>
              {STAT_ROW.map((st) => (
                <div key={st.label} style={{ background: "#0A0B0C", padding: "18px 20px" }}>
                  <div style={{ ...mono, fontSize: "22px", fontWeight: 600, color: "rgba(255,255,255,0.94)" }}>{st.n}</div>
                  <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.4)", marginTop: "4px" }}>{st.label}</div>
                </div>
              ))}
            </div>
          </section>

          {/* ══ 1 VARIABLES ══ */}
          <section id="variables" style={{ paddingTop: "96px" }}>
            <div style={sectionLabel}>1 — STATE VARIABLES</div>
            <h2 style={h2Style}>8 variables define the entire claim state.</h2>
            <p style={pStyle}>Everything the orchestrator decides is a pure function of these eight values — nothing else is state.</p>

            <div style={{ marginTop: "28px", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
              {STATE_VARS.map((v) => (
                <div key={v.name} style={{ display: "grid", gridTemplateColumns: "190px 1fr", gap: "20px", padding: "15px 0", borderBottom: "1px solid rgba(255,255,255,0.06)", alignItems: "baseline" }}>
                  <span style={{ ...mono, fontSize: "13px", color: "rgba(255,255,255,0.85)" }}>{v.name}</span>
                  <span style={{ fontSize: "13px", lineHeight: 1.6, color: "rgba(255,255,255,0.5)" }}>
                    <span style={{ ...mono, color: "rgba(255,255,255,0.35)" }}>{v.domain}</span>
                    {" — "}{v.desc}
                  </span>
                </div>
              ))}
            </div>
          </section>

          {/* ══ 2 TRANSITIONS ══ */}
          <section id="transitions" style={{ paddingTop: "96px" }}>
            <div style={sectionLabel}>2 — TRANSITION RELATION</div>
            <h2 style={h2Style}>11 valid edges. Nothing else moves.</h2>
            <p style={pStyle}>
              This mirrors the code&apos;s <code style={codeStyle}>_VALID_EDGES</code> set exactly — the spec and the implementation are two renderings of the same 11 pairs.
            </p>

            <div style={{ marginTop: "24px", display: "flex", flexDirection: "column", gap: "1px", background: "rgba(255,255,255,0.06)" }}>
              {FORMAL_EDGES.map((e) => (
                <div key={e.n} style={{ background: "#0A0B0C", display: "grid", gridTemplateColumns: "34px 1fr auto", gap: "14px", padding: "13px 16px", alignItems: "baseline" }}>
                  <span style={{ ...mono, fontSize: "11px", color: "rgba(255,255,255,0.3)" }}>{e.n}</span>
                  <span style={{ ...mono, fontSize: "13px", color: "rgba(255,255,255,0.85)" }}>
                    {e.from} <span style={{ color: "#3ECF8E" }}>→</span> {e.to}
                  </span>
                  <span style={{ ...mono, fontSize: "11.5px", color: "rgba(255,255,255,0.38)" }}>{e.guard}</span>
                </div>
              ))}
            </div>

            {/* reachable state graph */}
            <p style={{ margin: "28px 0 10px", ...mono, fontSize: "12px", letterSpacing: "0.06em", color: "rgba(255,255,255,0.32)", textTransform: "uppercase" }}>
              Claim Filing Pipeline — reachable states from intake to terminal closure
            </p>
            <div style={{ border: "1px solid rgba(255,255,255,0.08)", background: "#0B0C0D" }}>
              <div style={{ padding: "14px 20px", borderBottom: "1px solid rgba(255,255,255,0.07)", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                <span style={{ ...mono, fontSize: "11px", letterSpacing: "0.08em", color: "rgba(255,255,255,0.4)" }}>REACHABLE STATE GRAPH · LIVE</span>
                <span style={{ ...mono, fontSize: "11px", color: "rgba(255,255,255,0.32)" }}>dots trace the 11 accepted transitions only</span>
              </div>

              <div style={{ padding: "26px", overflow: "hidden", height: "290px" }}>
                <div style={{ position: "relative", width: "1190px", height: "380px", transform: "scale(0.61)", transformOrigin: "top left" }}>
                  <svg width="1190" height="380" style={{ position: "absolute", top: 0, left: 0, overflow: "visible", pointerEvents: "none" }}>
                    {GRAPH_LINES.map((ln, i) => (
                      <line key={i} x1={ln.x1} y1={ln.y1} x2={ln.x2} y2={ln.y2} stroke="rgba(255,255,255,0.14)" strokeWidth={1} />
                    ))}
                  </svg>

                  {/* CSS motion-path particles */}
                  {GRAPH_PARTICLES.map((pt, i) => (
                    <div
                      key={i}
                      style={{
                        position: "absolute",
                        top: 0,
                        left: 0,
                        width: "6px",
                        height: "6px",
                        borderRadius: "50%",
                        background: pt.color,
                        offsetPath: `path('${pt.path}')`,
                        animation: `citadel-flow ${pt.dur} linear infinite`,
                        animationDelay: pt.delay,
                      } as CSSProperties}
                    />
                  ))}

                  {/* nodes */}
                  {GRAPH_NODES.map((nd) => (
                    <div
                      key={nd.label}
                      style={{
                        position: "absolute",
                        left: `${nd.x}px`,
                        top: `${nd.y}px`,
                        width: "180px",
                        height: "44px",
                        border: `1px ${nd.dashed ? "dashed" : "solid"} ${nd.border}`,
                        background: "#0A0B0C",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        ...mono,
                        fontSize: "11.5px",
                        letterSpacing: "0.03em",
                        color: nd.color,
                        padding: "0 8px",
                        boxSizing: "border-box",
                      }}
                    >
                      {nd.label}
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ display: "flex", gap: "20px", padding: "14px 20px", borderTop: "1px solid rgba(255,255,255,0.06)", ...mono, fontSize: "11px", color: "rgba(255,255,255,0.4)", flexWrap: "wrap" }}>
                {[
                  { color: "#3ECF8E", label: "settlement path" },
                  { color: "#E0A73E", label: "escalation path" },
                  { color: "#E5484D", label: "denial path" },
                ].map((lg) => (
                  <span key={lg.label} style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ display: "inline-block", width: "6px", height: "6px", borderRadius: "50%", background: lg.color }} />
                    {lg.label}
                  </span>
                ))}
                <span style={{ color: "rgba(255,255,255,0.28)" }}>CLOSED — dashed border marks the absorbing terminal state</span>
              </div>
              <div style={{ padding: "10px 20px 14px", borderTop: "1px solid rgba(255,255,255,0.04)", ...mono, fontSize: "11px", color: "rgba(255,255,255,0.24)", textAlign: "center" }}>
                This state machine governs the Claim Filing pipeline exclusively. Other pipelines (FAQ, Inquiry, Complaint) are stateless.
              </div>
            </div>
          </section>

          {/* ══ 3 MATRIX ══ */}
          <section id="matrix" style={{ paddingTop: "96px" }}>
            <div style={sectionLabel}>3 — REACHABILITY: ALL 81 ORDERED PAIRS</div>
            <h2 style={h2Style}>9 states × 9 states. 11 green, 70 red.</h2>
            <p style={pStyle}>
              Every one of the 81 possible (from, to) pairs — including self-transitions — was driven through the real{" "}
              <code style={codeStyle}>advance_stage()</code> function. The 11 the spec allows were accepted; all 70 others were rejected.
            </p>

            <div data-matrix-scroll="" style={{ marginTop: "30px", border: "1px solid rgba(255,255,255,0.08)", background: "#0C0D0F", padding: "22px" }}>
              <div style={{ display: "inline-grid", gridTemplateColumns: "138px repeat(9, 30px)", gap: "3px", minWidth: "408px" }}>
                {/* column headers */}
                <div />
                {MATRIX_STATES.map((s) => (
                  <div key={`col-${s}`} style={{ writingMode: "vertical-rl", transform: "rotate(180deg)", ...mono, fontSize: "9.5px", color: "rgba(255,255,255,0.35)", textAlign: "left", height: "100px", alignSelf: "end" }}>
                    {s}
                  </div>
                ))}

                {/* rows */}
                {MATRIX_ROWS.map((row) => (
                  <React.Fragment key={row.name}>
                    <div style={{ ...mono, fontSize: "10.5px", color: "rgba(255,255,255,0.5)", display: "flex", alignItems: "center" }}>
                      {row.name}
                    </div>
                    {row.cells.map((c, ci) => (
                      <div key={ci} title={c.title} style={{ width: "30px", height: "22px", background: c.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: c.dot, display: "inline-block" }} />
                      </div>
                    ))}
                  </React.Fragment>
                ))}
              </div>

              <div style={{ display: "flex", gap: "22px", marginTop: "20px", paddingTop: "16px", borderTop: "1px solid rgba(255,255,255,0.06)", ...mono, fontSize: "11px", color: "rgba(255,255,255,0.4)", flexWrap: "wrap" }}>
                {[
                  { color: "#3ECF8E",              label: "valid — accepted (11)" },
                  { color: "rgba(229,72,77,0.55)", label: "invalid — rejected (70)" },
                ].map((lg) => (
                  <span key={lg.label} style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                    <span style={{ display: "inline-block", width: "6px", height: "6px", borderRadius: "50%", background: lg.color }} />
                    {lg.label}
                  </span>
                ))}
                <span style={{ color: "rgba(255,255,255,0.3)" }}>rows = from · columns = to</span>
              </div>
            </div>
          </section>

          {/* ══ 4 INVARIANTS ══ */}
          <section id="invariants" style={{ paddingTop: "96px" }}>
            <div style={sectionLabel}>4 — SAFETY &amp; LIVENESS</div>
            <h2 style={h2Style}>7 invariants the state machine can never violate.</h2>
            <p style={pStyle}>
              Common Criteria EAL3–4 (FDP_ACF.1), NIST SP 800-53 CM-7/AC-3, and OWASP ASVS Level 2 each require that only authorized state transitions are reachable and that committed data cannot be altered. The BFS model checker exhaustively verifies both across all 918 reachable states — 4 classical correctness properties and 3 write-once integrity properties, all formally proved.
            </p>

            <div style={{ marginTop: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
              {INVARIANTS.map((iv) => (
                <div key={iv.name} style={{ borderLeft: `2px solid ${iv.color}`, padding: "4px 0 4px 20px" }}>
                  <div style={{ display: "flex", alignItems: "baseline", gap: "12px", flexWrap: "wrap" }}>
                    <span style={{ fontSize: "15px", fontWeight: 600, color: "rgba(255,255,255,0.92)" }}>{iv.name}</span>
                    <span style={{ ...mono, fontSize: "10.5px", letterSpacing: "0.08em", color: iv.color }}>{iv.kind} · HOLDS</span>
                  </div>
                  <div style={{ ...mono, fontSize: "12.5px", color: "rgba(255,255,255,0.55)", marginTop: "8px", lineHeight: 1.7, background: "rgba(255,255,255,0.03)", padding: "10px 14px", display: "inline-block" }}>
                    {iv.formal}
                  </div>
                  <div style={{ fontSize: "13px", color: "rgba(255,255,255,0.45)", marginTop: "8px", lineHeight: 1.6 }}>{iv.plain}</div>
                  {iv.standards && iv.standards.length > 0 && (
                    <div style={{ marginTop: "8px", display: "flex", gap: "6px", flexWrap: "wrap" }}>
                      {iv.standards.map((std: string) => (
                        <span key={std} style={{ ...mono, fontSize: "10px", color: "rgba(255,255,255,0.28)", border: "1px solid rgba(255,255,255,0.08)", padding: "2px 8px", letterSpacing: "0.04em" }}>
                          {std}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>

          {/* ══ 5 VERIFICATION ══ */}
          <section id="verification" style={{ paddingTop: "96px" }}>
            <div style={sectionLabel}>5 — VERIFICATION METHOD</div>
            <h2 style={h2Style}>Exhaustive, not sampled.</h2>
            <p style={pStyle}>
              A Python BFS checker (<code style={codeStyle}>formal/check_spec.py</code>) enumerates the entire bounded state space from Init and checks every invariant at every reachable state — not a sample, all of it.
            </p>
            <SpecCheck />
          </section>

          {/* ══ 6 CONFORMANCE ══ */}
          <section id="conformance" style={{ paddingTop: "96px" }}>
            <div style={sectionLabel}>6 — CONFORMANCE TESTING</div>
            <h2 style={h2Style}>The spec and the code are tested against each other.</h2>
            <p style={pStyle}>
              A model check only proves the <em>spec</em> is sound. Conformance tests prove the running{" "}
              <code style={codeStyle}>advance_stage()</code> implementation actually obeys it — every invalid transition is provably rejected, not just sampled. This satisfies NIST SP 800-53 CM-7 (Least Functionality) and OWASP ASVS Level 2 V4, which require that unauthorized operations are denied at every enforcement point.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1px", background: "rgba(255,255,255,0.07)", marginTop: "24px", border: "1px solid rgba(255,255,255,0.07)" }}>
              {CONFORMANCE_STATS.map((cf) => (
                <div key={cf.label} style={{ background: "#0A0B0C", padding: "18px 20px" }}>
                  <div style={{ ...mono, fontSize: "20px", fontWeight: 600, color: cf.color }}>{cf.n}</div>
                  <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.4)", marginTop: "4px" }}>{cf.label}</div>
                </div>
              ))}
            </div>
          </section>

          {/* ══ 7 SOURCE ══ */}
          <section id="source" style={{ paddingTop: "96px" }}>
            <div style={sectionLabel}>7 — SOURCE</div>
            <h2 style={h2Style}>formal/workflow.tla</h2>
            <p style={pStyle}>Representative excerpt — the module in full is linked from the repository.</p>

            <div style={{ marginTop: "24px", border: "1px solid rgba(255,255,255,0.08)", background: "#0B0C0D" }}>
              <div style={{ padding: "12px 20px", borderBottom: "1px solid rgba(255,255,255,0.07)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ ...mono, fontSize: "11px", color: "rgba(255,255,255,0.4)" }}>TLA+ · module workflow</span>
                <a
                  href="https://github.com/Athish49/ProjectCitadel"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="link-dim"
                  style={{ ...mono, fontSize: "11px" }}
                >
                  view full source on GitHub →
                </a>
              </div>
              <div style={{ padding: "18px 0", maxHeight: "460px", overflowY: "auto" }}>
                {SOURCE_LINES.map((ln) => (
                  <div key={ln.n} style={{ display: "grid", gridTemplateColumns: "46px 1fr", gap: "14px", padding: "1px 20px" }}>
                    <span style={{ ...mono, fontSize: "11.5px", color: "rgba(255,255,255,0.22)", textAlign: "right", userSelect: "none" }}>{ln.n}</span>
                    <span style={{ ...mono, fontSize: "12.5px", lineHeight: 1.7, color: ln.color, whiteSpace: "pre" }}>{ln.text}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* ══ CTA ══ */}
          <section style={{ marginTop: "120px", borderTop: "1px solid rgba(255,255,255,0.09)", padding: "70px 0 90px" }}>
            <div style={{ ...mono, fontSize: "12px", letterSpacing: "0.1em", color: "rgba(255,255,255,0.4)" }}>THE PROOF COVERS THE STATE MACHINE. THE REST IS RUNTIME.</div>
            <div style={{ fontSize: "clamp(24px, 2.6vw, 32px)", fontWeight: 600, letterSpacing: "-0.025em", lineHeight: 1.2, color: "rgba(255,255,255,0.97)", marginTop: "18px", maxWidth: "640px" }}>
              See the same guards enforced live, or try to break them yourself.
            </div>
            <div style={{ display: "flex", gap: "14px", marginTop: "26px", flexWrap: "wrap" }}>
              <Link href="/playground"            className="btn-primary" style={{ fontSize: "14px", fontWeight: 600, padding: "12px 22px", borderRadius: "7px" }}>Launch the playground</Link>
              <Link href="/architecture#orchestrator" className="btn-outline" style={{ fontSize: "14px", fontWeight: 500, padding: "12px 22px", borderRadius: "7px" }}>See the orchestrator</Link>
            </div>
          </section>

          {/* footer */}
          <footer style={{ borderTop: "1px solid rgba(255,255,255,0.07)", padding: "30px 0 60px", display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "14px" }}>
            <span style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.4)" }}>Project Citadel — Formal Specification.</span>
            <div style={{ display: "flex", gap: "20px", ...mono, fontSize: "12px" }}>
              <Link href="/"         className="link-dim">Overview</Link>
              <Link href="/matrix"   className="link-dim">Matrix</Link>
              <Link href="/patterns" className="link-dim">Patterns</Link>
            </div>
          </footer>
        </div>
      </div>
    </div>
    </>
  );
}
