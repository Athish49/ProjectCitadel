import Link from "next/link";

export function FinalCTA() {
  return (
    <section style={{ marginTop: "clamp(88px,10vw,150px)", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
      <div
        data-rv
        style={{
          maxWidth: "1264px",
          margin: "0 auto",
          padding: "clamp(80px,10vw,140px) 32px",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "flex-end",
          justifyContent: "space-between",
          gap: "36px 64px",
        }}
      >
        <div style={{ maxWidth: "640px" }}>
          <h2
            style={{
              margin: 0,
              fontSize: "clamp(40px,6vw,80px)",
              lineHeight: 1,
              letterSpacing: "-0.04em",
              fontWeight: 600,
              color: "rgba(255,255,255,0.97)",
            }}
          >
            Try to break it.
          </h2>
          <p style={{ margin: "22px 0 0", fontSize: "17px", color: "rgba(255,255,255,0.7)", maxWidth: "520px" }}>
            Every payload runs the production pipeline. Find something new and it becomes a public issue with your trace
            attached.
          </p>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "12px" }}>
          <Link href="/playground" className="btn btn-p">
            Launch the playground
          </Link>
          <a href="https://github.com/Athish49/ProjectCitadel" target="_blank" rel="noopener noreferrer" className="btn btn-g">
            View source on GitHub
          </a>
        </div>
      </div>
    </section>
  );
}
