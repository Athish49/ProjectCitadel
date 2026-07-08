import type { Metadata } from "next";
import { PageNav } from "@/components/layout/page-nav";
import { Footer } from "@/components/layout/footer";
import { PatternExplorer } from "@/components/patterns/pattern-explorer";

export const metadata: Metadata = {
  title: "Defense Patterns — Project Citadel",
};

export default function PatternsPage() {
  return (
    <>
      <PageNav />

      <main style={{ paddingTop: "80px" }}>
        {/* Hero */}
        <section
          style={{
            padding: "160px 32px 0",
            maxWidth: "1240px",
            margin: "0 auto",
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
            <span>Defense Patterns</span>
          </div>

          <h1
            style={{
              margin: "26px 0 0",
              fontSize: "clamp(38px, 4vw, 60px)",
              lineHeight: 1.1,
              letterSpacing: "-0.032em",
              fontWeight: 600,
              maxWidth: "1020px",
            }}
          >
            <span style={{ color: "rgba(255,255,255,0.97)" }}>
              Twelve named shapes, not a pile of checks.
            </span>
            <span style={{ color: "rgba(255,255,255,0.42)" }}>
              {" "}Every defense in the system maps to one of these — a stated problem, an
              implementation, a citation, and a test that proves it.
            </span>
          </h1>

          {/* sub-stats */}
          <div
            style={{
              display: "flex",
              gap: "40px",
              marginTop: "48px",
              padding: "22px 0",
              borderTop: "1px solid rgba(255,255,255,0.09)",
              borderBottom: "1px solid rgba(255,255,255,0.09)",
              flexWrap: "wrap",
            }}
          >
            {[
              "12 patterns · 12/12 armed",
              "mapped across all 79 attack classes",
              "click a card for problem, implementation, citation, refs",
            ].map((s) => (
              <span
                key={s}
                style={{
                  fontFamily: "var(--font-geist-mono), monospace",
                  fontSize: "12.5px",
                  color: "rgba(255,255,255,0.5)",
                }}
              >
                {s}
              </span>
            ))}
          </div>
        </section>

        {/* Explorer */}
        <section
          style={{
            padding: "64px 32px 0",
            maxWidth: "1240px",
            margin: "0 auto",
          }}
        >
          <PatternExplorer />
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
              See the numbers behind these patterns.
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
                Open the 79-row matrix
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
