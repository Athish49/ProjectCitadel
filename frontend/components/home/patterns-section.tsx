import Link from "next/link";
import { SectionHeader } from "./section-header";
import { PATTERNS } from "@/lib/data/home";

export function PatternsSection() {
  return (
    <section style={{ maxWidth: "1264px", margin: "0 auto", padding: "clamp(88px,10vw,150px) 32px 0" }}>
      <SectionHeader
        eyebrow="03 — Defense patterns"
        title="Twelve patterns, not a pile of checks."
        lead="Each defense is a named shape with a citation, an implementation and a test."
        more={{ label: "All 12 patterns", href: "/patterns" }}
      />

      <div
        data-rv
        style={{
          marginTop: "48px",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit,minmax(200px,1fr))",
          gap: "1px",
          background: "rgba(255,255,255,0.08)",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        {PATTERNS.map((pt) => (
          <Link
            key={pt.id}
            href="/patterns"
            className="cell hover:bg-[#101113] transition-colors"
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: "14px",
              padding: "20px 20px",
              textDecoration: "none",
              minHeight: "64px",
              color: "inherit",
            }}
          >
            <span className="mono" style={{ fontSize: "12px", color: "rgba(255,255,255,0.55)", width: "26px" }}>
              {pt.id}
            </span>
            <span style={{ fontSize: "15px", fontWeight: 500 }}>{pt.name}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
