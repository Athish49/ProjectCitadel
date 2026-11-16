"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { label: "Architecture", href: "/architecture" },
  { label: "Playground", href: "/playground" },
  { label: "Patterns", href: "/patterns" },
  { label: "Matrix", href: "/matrix" },
  { label: "Adversary", href: "/adversary" },
  { label: "Formal", href: "/formal" },
];

/** Every page's header CTA reads "Launch playground → /playground",
 * except the Playground page itself, which points back at the architecture. */
const PLAYGROUND_CTA = { label: "Launch playground", href: "/playground" };
const ARCHITECTURE_CTA = { label: "Read the architecture", href: "/architecture" };

export function Nav() {
  const pathname = usePathname();
  const cta = pathname === "/playground" ? ARCHITECTURE_CTA : PLAYGROUND_CTA;

  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 20,
        background: "rgba(10,11,12,0.86)",
        backdropFilter: "blur(12px)",
        WebkitBackdropFilter: "blur(12px)",
        borderBottom: "1px solid rgba(255,255,255,0.07)",
      }}
    >
      <div
        style={{
          maxWidth: "1264px",
          margin: "0 auto",
          padding: "10px 32px",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "8px 28px",
        }}
      >
        <Link
          href="/"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            textDecoration: "none",
            fontWeight: 600,
            fontSize: "15px",
            minHeight: "44px",
            color: "rgba(255,255,255,0.95)",
          }}
        >
          <span
            className="mono"
            style={{
              width: "22px",
              height: "22px",
              border: "1px solid rgba(255,255,255,0.5)",
              borderRadius: "4px",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "11px",
            }}
          >
            C
          </span>
          Project Citadel
        </Link>

        <nav
          aria-label="Primary"
          className="nav-links"
          style={{ display: "flex", flexWrap: "wrap", gap: "0 26px" }}
        >
          {NAV_LINKS.map(({ label, href }) => (
            <Link
              key={href}
              href={href}
              className="nl"
              aria-current={pathname === href ? "page" : undefined}
              style={{
                fontSize: "14px",
                color: pathname === href ? "#fff" : "rgba(255,255,255,0.62)",
                textDecoration: "none",
                padding: "12px 2px",
                transition: "color 0.2s",
              }}
            >
              {label}
            </Link>
          ))}
        </nav>

        <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
          <a
            href="https://github.com/Athish49/ProjectCitadel"
            target="_blank"
            rel="noopener noreferrer"
            className="mono nl"
            style={{ fontSize: "13px", color: "rgba(255,255,255,0.62)" }}
          >
            GitHub
          </a>
          <Link
            href={cta.href}
            className="btn btn-p"
            style={{ minHeight: "40px", padding: "0 14px", fontSize: "13.5px" }}
          >
            {cta.label}
          </Link>
        </div>
      </div>
    </header>
  );
}
