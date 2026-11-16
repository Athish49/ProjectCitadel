import { SectionHeader } from "./section-header";
import { MATRIX_SUMMARY } from "@/lib/data/home";

export function MatrixSection() {
  return (
    <section style={{ maxWidth: "1264px", margin: "0 auto", padding: "clamp(88px,10vw,150px) 32px 0" }}>
      <SectionHeader
        eyebrow="04 — Attack–defense matrix"
        title="79 attack classes. Numbers, not adjectives."
        lead="Every row links to the payloads tried, the code that blocked them and the test that proves it."
        more={{ label: "View all 79 rows", href: "/matrix" }}
      />

      <div data-rv style={{ marginTop: "48px" }}>
        <div
          role="img"
          aria-label="43 live, 29 architectural, 7 out of scope"
          style={{ display: "flex", gap: "3px", height: "10px" }}
        >
          <div data-grow style={{ flex: `${MATRIX_SUMMARY.live} 1 0`, background: "var(--ok)" }} />
          <div data-grow style={{ flex: `${MATRIX_SUMMARY.architectural} 1 0`, background: "var(--blue)" }} />
          <div data-grow style={{ flex: `${MATRIX_SUMMARY.outOfScope} 1 0`, background: "rgba(255,255,255,0.28)" }} />
        </div>

        <div
          style={{
            marginTop: "28px",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))",
            gap: "28px 48px",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "12px" }}>
              <span className="mono" style={{ fontSize: "40px", lineHeight: 1, fontWeight: 500, color: "var(--ok)" }}>
                {MATRIX_SUMMARY.live}
              </span>
              <span className="eb">Live</span>
            </div>
            <p style={{ margin: "12px 0 0", fontSize: "14.5px", color: "rgba(255,255,255,0.7)" }}>
              Automated suites with real payloads. Results published per run.
            </p>
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "12px" }}>
              <span className="mono" style={{ fontSize: "40px", lineHeight: 1, fontWeight: 500, color: "var(--blue)" }}>
                {MATRIX_SUMMARY.architectural}
              </span>
              <span className="eb">Architectural</span>
            </div>
            <p style={{ margin: "12px 0 0", fontSize: "14.5px", color: "rgba(255,255,255,0.7)" }}>
              Inapplicable by construction. Verified by assertion tests in CI.
            </p>
          </div>
          <div>
            <div style={{ display: "flex", alignItems: "baseline", gap: "12px" }}>
              <span className="mono" style={{ fontSize: "40px", lineHeight: 1, fontWeight: 500, color: "rgba(255,255,255,0.7)" }}>
                {MATRIX_SUMMARY.outOfScope}
              </span>
              <span className="eb">Out of scope</span>
            </div>
            <p style={{ margin: "12px 0 0", fontSize: "14.5px", color: "rgba(255,255,255,0.7)" }}>
              No model is trained here, so no training-data attacks.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
