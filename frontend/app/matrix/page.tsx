import type { Metadata } from "next";
import { Nav } from "@/components/layout/nav";
import { Footer } from "@/components/layout/footer";
import { MatrixTable } from "@/components/matrix/matrix-table";
import { ScrollRevealRoot } from "@/components/matrix/scroll-reveal-root";
import { LIVE_COUNT, ARCH_COUNT, OOS_COUNT } from "@/lib/data/matrix";

export const metadata: Metadata = {
  title: "Attack–Defense Matrix — Project Citadel",
};

const mono: React.CSSProperties = { fontFamily: "var(--font-geist-mono), monospace" };

export default function MatrixPage() {
  return (
    <ScrollRevealRoot style={{ background: "#0A0B0C", color: "rgba(255,255,255,0.95)", minHeight: "100vh" }}>
      <Nav />

      <main>
        {/* Hero */}
        <section style={{ maxWidth: "1264px", margin: "0 auto", padding: "clamp(64px,9vw,120px) 32px 0" }}>
          <div data-rv className="eb">Attack–defense matrix</div>

          <h1
            data-rv
            style={{
              margin: "22px 0 0",
              fontSize: "clamp(40px,6.4vw,84px)",
              lineHeight: 1,
              letterSpacing: "-0.04em",
              fontWeight: 600,
              maxWidth: "960px",
              transitionDelay: "80ms",
            }}
          >
            79 attack classes. Numbers, not adjectives.
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
            Each class is classified, linked to a named defense and tested where a test is possible.
          </p>

          <div data-rv style={{ marginTop: "56px", transitionDelay: "240ms" }}>
            <div
              role="img"
              aria-label={`${LIVE_COUNT} live, ${ARCH_COUNT} architectural, ${OOS_COUNT} out of scope`}
              style={{ display: "flex", gap: "3px", height: "10px" }}
            >
              <div data-grow style={{ flex: `${LIVE_COUNT} 1 0`, background: "#3ecf8e" }} />
              <div data-grow style={{ flex: `${ARCH_COUNT} 1 0`, background: "#5b8def" }} />
              <div data-grow style={{ flex: `${OOS_COUNT} 1 0`, background: "rgba(255,255,255,0.28)" }} />
            </div>

            <div
              style={{
                marginTop: "24px",
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit,minmax(240px,1fr))",
                gap: "24px 48px",
              }}
            >
              <div>
                <div style={{ display: "flex", alignItems: "baseline", gap: "12px" }}>
                  <span style={{ ...mono, fontSize: "36px", lineHeight: 1, fontWeight: 500, color: "#3ecf8e" }}>
                    {LIVE_COUNT}
                  </span>
                  <span className="eb">Live</span>
                </div>
                <p style={{ margin: "10px 0 0", fontSize: "14px", color: "rgba(255,255,255,0.68)" }}>
                  Tested in CI with real payloads.
                </p>
              </div>
              <div>
                <div style={{ display: "flex", alignItems: "baseline", gap: "12px" }}>
                  <span style={{ ...mono, fontSize: "36px", lineHeight: 1, fontWeight: 500, color: "#5b8def" }}>
                    {ARCH_COUNT}
                  </span>
                  <span className="eb">Architectural</span>
                </div>
                <p style={{ margin: "10px 0 0", fontSize: "14px", color: "rgba(255,255,255,0.68)" }}>
                  Prevented by design, not runtime checks.
                </p>
              </div>
              <div>
                <div style={{ display: "flex", alignItems: "baseline", gap: "12px" }}>
                  <span style={{ ...mono, fontSize: "36px", lineHeight: 1, fontWeight: 500, color: "rgba(255,255,255,0.7)" }}>
                    {OOS_COUNT}
                  </span>
                  <span className="eb">Out of scope</span>
                </div>
                <p style={{ margin: "10px 0 0", fontSize: "14px", color: "rgba(255,255,255,0.68)" }}>
                  Acknowledged, not in the threat model.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Filter bar + table */}
        <section style={{ maxWidth: "1264px", margin: "0 auto", padding: "64px 32px 0" }}>
          <div data-rv style={{ transitionDelay: "100ms" }}>
            <MatrixTable />
          </div>
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
                maxWidth: "680px",
              }}
            >
              Every defense has a name.
            </h2>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "12px" }}>
              <a className="btn btn-p" href="/patterns">See the 12 patterns</a>
              <a className="btn btn-g" href="/playground">Try the playground</a>
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </ScrollRevealRoot>
  );
}
