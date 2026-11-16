import type { Metadata } from "next";
import { Nav } from "@/components/layout/nav";
import { Footer } from "@/components/layout/footer";
import { ScrollReveal } from "@/components/layout/scroll-reveal";
import { TopologyDiagram } from "@/components/architecture/topology-diagram";
import { DefenseDepth } from "@/components/architecture/defense-depth";
import { ControlPlaneDiagram } from "@/components/architecture/control-plane-diagram";
import { Mechanisms } from "@/components/architecture/mechanisms";
import { HERO_STATS, LEAST_PRIVILEGE, DESIGN_DECISIONS } from "@/lib/data/architecture";
import styles from "@/components/architecture/architecture.module.css";

export const metadata: Metadata = {
  title: "Architecture — Project Citadel",
  description: "Project Citadel assumes any model can be hijacked, then limits what a hijacked one can reach.",
};

// Section padding the design overrides for this page: .sec's base padding is
// clamp(72px,8vw,120px) 32px 0, but Architecture.dc.html's own stylesheet
// re-declares padding-top later in the same <style> block as
// clamp(72px,7vw,104px) — that second rule wins the cascade, so this page
// uses the smaller value rather than the (larger) one the shared brief named.
const SEC: React.CSSProperties = { maxWidth: "1264px", margin: "0 auto", padding: "clamp(72px,7vw,104px) 32px 0" };
const EB: React.CSSProperties = { fontFamily: "var(--font-geist-mono), monospace", fontSize: 12, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.58)" };
const H2: React.CSSProperties = { margin: "18px 0 0", fontSize: "clamp(28px,3.4vw,44px)", lineHeight: 1.08, letterSpacing: "-0.03em", fontWeight: 600 };
const LEAD: React.CSSProperties = { margin: "16px 0 0", fontSize: 17, color: "rgba(255,255,255,0.7)", maxWidth: 620 };
const TH: React.CSSProperties = { textAlign: "left", padding: "13px 18px", fontSize: 11, fontWeight: 400, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.58)", borderBottom: "1px solid rgba(255,255,255,0.1)" };
const TD: React.CSSProperties = { padding: "15px 18px", borderBottom: "1px solid rgba(255,255,255,0.06)", fontSize: 14, verticalAlign: "top" };

export default function ArchitecturePage() {
  return (
    <div data-page="architecture" style={{ background: "#0A0B0C", color: "rgba(255,255,255,0.95)", minHeight: "100vh" }}>
      <ScrollReveal threshold={0.03} />
      <Nav />

      <main>
        {/* ── Hero ── */}
        <section style={{ maxWidth: "1264px", margin: "0 auto", padding: "clamp(64px,9vw,120px) 32px 0" }}>
          <div data-rv className="eb">Architecture</div>
          <h1
            data-rv
            style={{
              margin: "22px 0 0", fontSize: "clamp(40px,6.4vw,84px)", lineHeight: 1,
              letterSpacing: "-0.04em", fontWeight: 600, maxWidth: 940, transitionDelay: "80ms",
            }}
          >
            Blast radius is a design decision.
          </h1>
          <p
            data-rv
            style={{
              margin: "26px 0 0", maxWidth: 600, fontSize: "clamp(17px,1.5vw,19px)",
              lineHeight: 1.5, color: "rgba(255,255,255,0.7)", transitionDelay: "160ms",
            }}
          >
            Project Citadel assumes any model can be hijacked, then limits what a hijacked one can reach.
          </p>
          <div
            data-rv
            style={{
              marginTop: 56, display: "grid",
              gridTemplateColumns: "repeat(auto-fit,minmax(min(180px,100%),1fr))",
              gap: "1px", background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.08)",
              transitionDelay: "240ms",
            }}
          >
            {HERO_STATS.map((s) => (
              <div key={s.label} className="cell" style={{ padding: "20px 20px 22px" }}>
                <div className="mono" style={{ fontSize: 28, lineHeight: 1, fontWeight: 500, color: s.color }}>{s.value}</div>
                <div style={{ marginTop: 10, fontSize: 13, color: "rgba(255,255,255,0.62)" }}>{s.label}</div>
              </div>
            ))}
          </div>
        </section>

        {/* ── 01 System map ── */}
        <section style={SEC}>
          <div data-rv>
            <div className="eb" style={EB}>01 — System map</div>
            <h2 style={H2}>Trust increases left to right.</h2>
            <p style={LEAD}>Every arrow is a real hand-off between two components. Select any component to see what it does.</p>
          </div>
          <div data-rv style={{ marginTop: 44 }}>
            <TopologyDiagram />
          </div>
        </section>

        {/* ── 02 Defence in depth ── */}
        <section style={SEC}>
          <div data-rv>
            <div className="eb" style={EB}>02 — Defence in depth</div>
            <h2 style={H2}>One request. Eight chances to stop it.</h2>
            <p style={LEAD}>No layer is trusted to be perfect. Pick an attack and watch where it dies, and which later layers would have caught it anyway.</p>
          </div>
          <div data-rv style={{ marginTop: 44 }}>
            <DefenseDepth />
          </div>
          <p data-rv style={{ margin: "20px 0 0", fontSize: 14, color: "rgba(255,255,255,0.62)" }}>
            Six of the eight layers are plain code. A model that is talked round cannot talk the code round.
          </p>
        </section>

        {/* ── 03 Control plane ── */}
        <section style={SEC} id="orchestrator">
          <div data-rv>
            <div className="eb" style={EB}>03 — Control plane</div>
            <h2 style={H2}>Models propose. Code decides.</h2>
            <p style={LEAD}>An actor can only suggest the next step. The orchestrator checks that suggestion against facts in the database, which no prompt can change.</p>
          </div>
          <div data-rv style={{ marginTop: 44 }}>
            <ControlPlaneDiagram />
          </div>
          <p data-rv style={{ margin: "20px 0 0", fontSize: 14, color: "rgba(255,255,255,0.62)" }}>
            The state machine is model-checked in all 918 reachable states.{" "}
            <a href="/formal" style={{ color: "rgba(255,255,255,0.95)" }}>See the proof</a>
          </p>
        </section>

        {/* ── 04 Least privilege ── */}
        <section style={SEC}>
          <div data-rv>
            <div className="eb" style={EB}>04 — Least privilege</div>
            <h2 style={H2}>If a model is hijacked, this is all it gets.</h2>
            <p style={LEAD}>Six models, six different keyrings. Only the parser reads raw user text, and it is the one with no tools.</p>
          </div>
          <div data-rv className="panel" style={{ marginTop: 44, overflowX: "auto" }}>
            <table className={styles.table}>
              <thead>
                <tr>
                  {["Model", "Reads raw user text", "Tools", "Data it can read", "Can write", "Worst case if hijacked"].map((h, i) => (
                    <th key={h} scope="col" className="mono" style={{ ...TH, textAlign: i === 2 ? "center" : "left" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {LEAST_PRIVILEGE.map((r) => (
                  <tr key={r.model}>
                    <td style={{ ...TD, whiteSpace: "nowrap" }}><span style={{ fontWeight: 500 }}>{r.model}</span></td>
                    <td style={TD}>
                      {r.reads
                        ? <span style={{ color: "#e2a336", fontWeight: 500 }}>Yes</span>
                        : <span style={{ color: "rgba(255,255,255,0.62)" }}>No</span>}
                    </td>
                    <td style={{ ...TD, textAlign: "center" }}><span className="mono">{r.tools}</span></td>
                    <td style={{ ...TD, color: "rgba(255,255,255,0.78)" }}>{r.dataRead}</td>
                    <td style={{ ...TD, color: "rgba(255,255,255,0.78)" }}>{r.canWrite}</td>
                    <td style={{ ...TD, color: "rgba(255,255,255,0.9)", minWidth: 280 }}>{r.worstCase}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── 05 Mechanisms ── */}
        <section style={SEC}>
          <div data-rv>
            <div className="eb" style={EB}>05 — Mechanisms</div>
            <h2 style={H2}>Five mechanisms hold the boundaries.</h2>
            <p style={LEAD}>Each is ordinary engineering, chosen so that no single failure is enough.</p>
          </div>
          <div data-rv>
            <Mechanisms />
          </div>
        </section>

        {/* ── 06 Design decisions ── */}
        <section style={SEC}>
          <div data-rv>
            <div className="eb" style={EB}>06 — Design decisions</div>
            <h2 style={H2}>Seven choices, and what each one costs.</h2>
          </div>
          <div data-rv className="panel" style={{ marginTop: 44, overflowX: "auto" }}>
            <table className={styles.table} style={{ minWidth: 860 }}>
              <thead>
                <tr>
                  {["We chose", "Instead of", "Because", "Trade-off"].map((h) => (
                    <th key={h} scope="col" className="mono" style={TH}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {DESIGN_DECISIONS.map((r) => (
                  <tr key={r.chose}>
                    <td style={TD}><span style={{ fontWeight: 500 }}>{r.chose}</span></td>
                    <td style={{ ...TD, color: "rgba(255,255,255,0.62)" }}>{r.instead}</td>
                    <td style={{ ...TD, color: "rgba(255,255,255,0.88)" }}>{r.because}</td>
                    <td style={{ ...TD, color: "rgba(255,255,255,0.72)" }}>{r.tradeoff}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Final CTA ── */}
        <section style={{ marginTop: "clamp(88px,10vw,140px)", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
          <div
            data-rv
            style={{
              maxWidth: "1264px", margin: "0 auto", padding: "clamp(72px,9vw,120px) 32px",
              display: "flex", flexWrap: "wrap", alignItems: "flex-end", justifyContent: "space-between", gap: "32px 64px",
            }}
          >
            <div style={{ maxWidth: 680 }}>
              <h2 style={{ margin: 0, fontSize: "clamp(30px,4.2vw,54px)", lineHeight: 1.04, letterSpacing: "-0.035em", fontWeight: 600 }}>
                Now watch it hold under fire.
              </h2>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "12px" }}>
              <a className="btn btn-p" href="/playground">Launch the playground</a>
              <a className="btn btn-g" href="/formal">See the proof</a>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
}
