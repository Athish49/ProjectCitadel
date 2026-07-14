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

export function Nav() {
  const pathname = usePathname();

  return (
    <nav
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        zIndex: 100,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 32px",
        height: "60px",
        background: "rgba(10,11,12,0.82)",
        backdropFilter: "blur(14px)",
        WebkitBackdropFilter: "blur(14px)",
        borderBottom: "1px solid rgba(255,255,255,0.07)",
      }}
    >
      {/* Logo */}
      <Link
        href="/"
        style={{
          display: "flex",
          alignItems: "center",
          gap: "10px",
          color: "rgba(255,255,255,0.95)",
        }}
      >
        <span
          style={{
            display: "inline-flex",
            width: "22px",
            height: "22px",
            border: "1.5px solid rgba(255,255,255,0.9)",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: "var(--font-geist-mono), monospace",
            fontSize: "11px",
            fontWeight: 600,
            flexShrink: 0,
          }}
        >
          C
        </span>
        <span
          style={{
            fontWeight: 600,
            fontSize: "15px",
            letterSpacing: "-0.01em",
          }}
        >
          Citadel
        </span>
      </Link>

      {/* Nav links — hidden below 1120px via media query in globals.css */}
      <div
        className="nav-links"
        style={{
          display: "flex",
          alignItems: "center",
          gap: "26px",
          fontSize: "13.5px",
        }}
      >
        {NAV_LINKS.map(({ label, href }) => (
          <Link
            key={href}
            href={href}
            style={{
              color:
                pathname === href
                  ? "rgba(255,255,255,0.95)"
                  : "rgba(255,255,255,0.55)",
              transition: "color 0.15s",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.color = "rgba(255,255,255,0.95)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.color =
                pathname === href
                  ? "rgba(255,255,255,0.95)"
                  : "rgba(255,255,255,0.55)")
            }
          >
            {label}
          </Link>
        ))}
      </div>

      {/* Right actions */}
      <div style={{ display: "flex", alignItems: "center", gap: "18px" }}>
        <a
          href="https://github.com/Athish49/ProjectCitadel"
          target="_blank"
          rel="noopener noreferrer"
          style={{
            fontSize: "13.5px",
            fontFamily: "var(--font-geist-mono), monospace",
            color: "rgba(255,255,255,0.55)",
          }}
          onMouseEnter={(e) =>
            (e.currentTarget.style.color = "rgba(255,255,255,0.95)")
          }
          onMouseLeave={(e) =>
            (e.currentTarget.style.color = "rgba(255,255,255,0.55)")
          }
        >
          GitHub
        </a>
        <Link
          href="/playground"
          className="btn-primary"
          style={{
            fontSize: "13.5px",
            fontWeight: 600,
            padding: "8px 16px",
            borderRadius: "6px",
            whiteSpace: "nowrap",
          }}
        >
          Launch the playground
        </Link>
      </div>
    </nav>
  );
}
