import type { Metadata } from "next";
import { PageNav } from "@/components/layout/page-nav";
import { Footer } from "@/components/layout/footer";
import { AdversaryLive } from "@/components/adversary/adversary-live";

export const metadata: Metadata = {
  title: "Adversarial Agent — Project Citadel",
};

export default function AdversaryPage() {
  return (
    <>
      <PageNav />

      <main style={{ paddingTop: "80px" }}>
        <section
          style={{
            maxWidth: "1240px",
            margin: "0 auto",
            padding: "80px 32px 0",
          }}
        >
          {/* breadcrumb */}
          <div
            style={{
              fontFamily: "var(--font-geist-mono), monospace",
              fontSize: "12px",
              letterSpacing: "0.08em",
              color: "rgba(255,255,255,0.45)",
              textTransform: "uppercase",
            }}
          >
            <a href="/" style={{ color: "rgba(255,255,255,0.45)" }}>
              Project Citadel
            </a>
            <span style={{ color: "rgba(255,255,255,0.2)" }}> / </span>
            <span>Adversarial Agent</span>
          </div>

          <h1
            style={{
              margin: "22px 0 0",
              fontSize: "clamp(38px, 4vw, 60px)",
              lineHeight: 1.1,
              letterSpacing: "-0.032em",
              fontWeight: 600,
              maxWidth: "1040px",
              color: "rgba(255,255,255,0.97)",
            }}
          >
            An autonomous attacker is running right now.
          </h1>

          {/* Dynamic content: stats + feed + sidebar */}
          <AdversaryLive />
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
              Every attempt above traces to a named pattern and a numbered row.
            </div>
            <div style={{ display: "flex", gap: "14px", flexWrap: "wrap" }}>
              <a
                href="/matrix"
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
                See the full 79-row matrix
              </a>
              <a
                href="/patterns"
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
                Read the 12 defence patterns
              </a>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </>
  );
}
