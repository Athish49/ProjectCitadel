import type { Metadata } from "next";
import { Nav } from "@/components/layout/nav";
import { Footer } from "@/components/layout/footer";
import { PatternExplorer } from "@/components/patterns/pattern-explorer";
import { ScrollReveal } from "@/components/patterns/scroll-reveal";

export const metadata: Metadata = {
  title: "Defense Patterns — Project Citadel",
};

export default function PatternsPage() {
  return (
    <>
      <ScrollReveal />
      <Nav />

      <main>
        {/* Hero */}
        <section
          style={{
            maxWidth: "1264px",
            margin: "0 auto",
            padding: "clamp(64px,9vw,120px) 32px 0",
          }}
        >
          <div data-rv className="eb">
            Defense patterns
          </div>
          <h1
            data-rv
            style={{
              margin: "22px 0 0",
              fontSize: "clamp(40px,6.4vw,84px)",
              lineHeight: 1,
              letterSpacing: "-0.04em",
              fontWeight: 600,
              maxWidth: "900px",
              transitionDelay: "80ms",
            }}
          >
            Twelve named shapes.
          </h1>
          <p
            data-rv
            style={{
              margin: "26px 0 0",
              maxWidth: "560px",
              fontSize: "clamp(17px,1.5vw,19px)",
              lineHeight: 1.5,
              color: "rgba(255,255,255,0.7)",
              transitionDelay: "160ms",
            }}
          >
            Every defense maps to one of them: a stated problem, an implementation, a test and an
            honest limit.
          </p>
          <div
            data-rv
            style={{
              marginTop: "28px",
              display: "flex",
              flexWrap: "wrap",
              gap: "8px 28px",
              transitionDelay: "240ms",
            }}
          >
            <span className="mono" style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.7)" }}>
              <span style={{ color: "#3ecf8e" }}>12 / 12</span> armed
            </span>
            <span className="mono" style={{ fontSize: "12.5px", color: "rgba(255,255,255,0.7)" }}>
              mapped across 79 attack classes
            </span>
          </div>
        </section>

        {/* Explorer */}
        <section style={{ maxWidth: "1264px", margin: "0 auto", padding: "56px 32px 0" }}>
          <PatternExplorer />
        </section>

        {/* CTA */}
        <section style={{ marginTop: "clamp(88px,10vw,140px)", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
          <div
            data-rv
            style={{
              maxWidth: "1264px",
              margin: "0 auto",
              padding: "clamp(72px,9vw,120px) 32px",
              display: "flex",
              flexWrap: "wrap",
              alignItems: "flex-end",
              justifyContent: "space-between",
              gap: "32px 64px",
            }}
          >
            <h2
              style={{
                margin: 0,
                fontSize: "clamp(34px,5vw,64px)",
                lineHeight: 1.02,
                letterSpacing: "-0.04em",
                fontWeight: 600,
                maxWidth: "640px",
              }}
            >
              See the numbers behind them.
            </h2>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "12px" }}>
              <a className="btn btn-p" href="/matrix">
                Open the 79-row matrix
              </a>
              <a className="btn btn-g" href="/playground">
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
