import type { Metadata } from "next";
import { PageNav } from "@/components/layout/page-nav";
import { Footer } from "@/components/layout/footer";
import { MatrixTable } from "@/components/matrix/matrix-table";
import { LIVE_COUNT, ARCH_COUNT, OOS_COUNT } from "@/lib/data/matrix";

export const metadata: Metadata = {
  title: "Attack–Defense Matrix — Project Citadel",
};

export default function MatrixPage() {
  return (
    <>
      <PageNav />

      <main style={{ paddingTop: "80px" }}>
        {/* Hero */}
        <section
          style={{
            maxWidth: "1200px",
            margin: "0 auto",
            padding: "72px 40px 48px",
          }}
        >
          {/* breadcrumb */}
          <div
            style={{
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "11.5px",
              letterSpacing: "0.12em",
              color: "rgba(255,255,255,0.35)",
              marginBottom: "28px",
            }}
          >
            Project Citadel / Attack–Defense Matrix
          </div>

          {/* headline */}
          <h1
            style={{
              fontSize: "clamp(34px, 5vw, 58px)",
              fontWeight: 700,
              letterSpacing: "-0.02em",
              lineHeight: 1.08,
              margin: "0 0 18px",
              color: "rgba(255,255,255,0.97)",
              maxWidth: "780px",
            }}
          >
            79 attack classes.{" "}
            <span style={{ color: "rgba(255,255,255,0.38)" }}>
              Numbers, never adjectives.
            </span>
          </h1>

          <p
            style={{
              fontSize: "16px",
              color: "rgba(255,255,255,0.55)",
              lineHeight: 1.65,
              maxWidth: "580px",
              margin: "0 0 52px",
            }}
          >
            Every known attack class against production agentic systems — classified,
            linked to a named defence, and continuously tested.
          </p>

          {/* stats grid */}
          <div
            data-mstats-grid=""
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: "1px",
              background: "rgba(255,255,255,0.07)",
              border: "1px solid rgba(255,255,255,0.07)",
              maxWidth: "600px",
            }}
          >
            {[
              { n: LIVE_COUNT,  label: "LIVE",                      color: "#3ECF8E", desc: "tested in CI with real payloads" },
              { n: ARCH_COUNT,  label: "ARCHITECTURAL",              color: "#5FA8A0", desc: "prevented by design, not runtime checks" },
              { n: OOS_COUNT,   label: "OUT-OF-SCOPE",               color: "rgba(255,255,255,0.35)", desc: "acknowledged, not in threat model" },
            ].map(({ n, label, color, desc }) => (
              <div
                key={label}
                style={{
                  padding: "24px 20px",
                  background: "#0B0C0E",
                }}
              >
                <div
                  style={{
                    fontFamily: "var(--font-geist-mono), monospace",
                    fontSize: "32px",
                    fontWeight: 700,
                    color,
                    marginBottom: "6px",
                    lineHeight: 1,
                  }}
                >
                  {n}
                </div>
                <div
                  style={{
                    fontFamily: "var(--font-geist-mono), monospace",
                    fontSize: "10.5px",
                    letterSpacing: "0.1em",
                    color: "rgba(255,255,255,0.4)",
                    marginBottom: "6px",
                  }}
                >
                  {label}
                </div>
                <div
                  style={{
                    fontSize: "12px",
                    color: "rgba(255,255,255,0.35)",
                    lineHeight: 1.4,
                  }}
                >
                  {desc}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Table section */}
        <section
          style={{
            maxWidth: "1200px",
            margin: "0 auto",
            padding: "0 40px 80px",
          }}
        >
          <MatrixTable />
        </section>

        {/* CTA */}
        <section
          style={{
            marginTop: "120px",
            borderTop: "1px solid rgba(255,255,255,0.09)",
            background: "#0B0C0E",
          }}
        >
          <div
            style={{
              maxWidth: "1240px",
              margin: "0 auto",
              padding: "90px 32px",
              display: "flex",
              flexDirection: "column",
              alignItems: "flex-start",
              gap: "24px",
            }}
          >
            <div
              style={{
                fontSize: "clamp(30px, 3.4vw, 46px)",
                fontWeight: 600,
                letterSpacing: "-0.03em",
                lineHeight: 1.14,
                color: "rgba(255,255,255,0.97)",
                maxWidth: "760px",
              }}
            >
              Every row traces back to a named pattern.
            </div>
            <div style={{ display: "flex", gap: "14px", flexWrap: "wrap" }}>
              <a
                href="/patterns"
                className="btn-primary"
                style={{
                  display: "inline-block",
                  fontSize: "14.5px",
                  fontWeight: 600,
                  padding: "13px 24px",
                  borderRadius: "7px",
                  textDecoration: "none",
                }}
              >
                See the 12 defence patterns
              </a>
              <a
                href="/playground"
                className="btn-outline"
                style={{
                  display: "inline-block",
                  fontSize: "14.5px",
                  fontWeight: 500,
                  padding: "13px 24px",
                  borderRadius: "7px",
                  textDecoration: "none",
                  background: "transparent",
                }}
              >
                Try the playground
              </a>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}
