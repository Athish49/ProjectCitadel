import { FooterEmail } from "./footer-email";

export function Footer() {
  return (
    <footer style={{ borderTop: "1px solid rgba(255,255,255,0.08)" }}>
      <div
        style={{
          maxWidth: "1264px",
          margin: "0 auto",
          padding: "28px 32px 40px",
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "space-between",
          gap: "16px 40px",
          fontSize: "13px",
          color: "rgba(255,255,255,0.55)",
        }}
      >
        <span>Project Citadel · Built by Athish Gopal Rajesh</span>
        <span style={{ display: "flex", flexWrap: "wrap", gap: "6px 24px" }}>
          <a
            href="https://grathish.vercel.app/"
            target="_blank"
            rel="noopener noreferrer"
            className="nl"
            style={{ fontSize: "13px", padding: 0 }}
          >
            Portfolio
          </a>
          <a
            href="https://www.linkedin.com/in/athishgr/"
            target="_blank"
            rel="noopener noreferrer"
            className="nl"
            style={{ fontSize: "13px", padding: 0 }}
          >
            LinkedIn
          </a>
          <a
            href="https://github.com/Athish49/ProjectCitadel"
            target="_blank"
            rel="noopener noreferrer"
            className="nl"
            style={{ fontSize: "13px", padding: 0 }}
          >
            GitHub
          </a>
          <FooterEmail />
        </span>
      </div>
    </footer>
  );
}
