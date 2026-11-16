import { MoreLink } from "./more-link";
import { RESIDUAL_RISKS, VERIFICATION_STATS } from "@/lib/data/home";

/** Combines "06 — Verification" and "07 — Residual risk" — the two columns
 * that sit side by side in a single section in Main.dc.html. */
export function VerificationRiskSection() {
  return (
    <section style={{ maxWidth: "1264px", margin: "0 auto", padding: "clamp(88px,10vw,150px) 32px 0" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(340px,1fr))", gap: "72px 64px" }}>
        {/* 06 — Verification */}
        <div data-rv>
          <div className="eb">06 — Verification</div>
          <h2
            style={{
              margin: "18px 0 0",
              fontSize: "clamp(28px,3vw,38px)",
              lineHeight: 1.08,
              letterSpacing: "-0.03em",
              fontWeight: 600,
              color: "rgba(255,255,255,0.97)",
            }}
          >
            Proven, not promised.
          </h2>
          <p style={{ margin: "16px 0 0", fontSize: "16px", color: "rgba(255,255,255,0.7)", maxWidth: "460px" }}>
            The workflow is specified in TLA+. Every action lands in a hash-chained log you can verify.
          </p>

          <div
            style={{
              marginTop: "32px",
              display: "grid",
              gridTemplateColumns: "repeat(3, minmax(0,1fr))",
              gap: "1px",
              background: "rgba(255,255,255,0.08)",
              border: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            {VERIFICATION_STATS.map((v) => (
              <div key={v.label} className="cell hover:bg-[#101113] transition-colors" style={{ padding: "18px 16px" }}>
                <div className="mono" style={{ fontSize: "22px", fontWeight: 500 }}>
                  {v.value}
                </div>
                <div style={{ marginTop: "6px", fontSize: "12.5px", color: "rgba(255,255,255,0.55)" }}>{v.label}</div>
              </div>
            ))}
          </div>

          <MoreLink href="/formal" style={{ marginTop: "20px" }}>
            See the proofs
          </MoreLink>
        </div>

        {/* 07 — Residual risk */}
        <div data-rv style={{ transitionDelay: "120ms" }}>
          <div className="eb">07 — Residual risk</div>
          <h2
            style={{
              margin: "18px 0 0",
              fontSize: "clamp(28px,3vw,38px)",
              lineHeight: 1.08,
              letterSpacing: "-0.03em",
              fontWeight: 600,
              color: "rgba(255,255,255,0.97)",
            }}
          >
            What still doesn&rsquo;t work.
          </h2>
          <p style={{ margin: "16px 0 0", fontSize: "16px", color: "rgba(255,255,255,0.7)", maxWidth: "460px" }}>
            Thirteen named limitations, each published with its root cause.
          </p>

          <div style={{ marginTop: "32px", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
            {RESIDUAL_RISKS.map((rr) => (
              <div
                key={rr.id}
                style={{ display: "flex", gap: "18px", padding: "15px 0", borderBottom: "1px solid rgba(255,255,255,0.08)" }}
              >
                <span className="mono" style={{ fontSize: "12px", color: "var(--warn)", paddingTop: "2px" }}>
                  {rr.id}
                </span>
                <span style={{ fontSize: "15px" }}>{rr.name}</span>
              </div>
            ))}
          </div>

          <MoreLink href="https://github.com/Athish49/ProjectCitadel" external style={{ marginTop: "20px" }}>
            Read the full register
          </MoreLink>
        </div>
      </div>
    </section>
  );
}
