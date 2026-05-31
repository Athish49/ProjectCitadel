import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_LINKS = [
  { href: "/playground", label: "Playground" },
  { href: "/architecture", label: "Architecture" },
  { href: "/formal", label: "Formal" },
  { href: "/matrix", label: "Matrix" },
  { href: "/patterns", label: "Patterns" },
  { href: "/adversary", label: "Adversary" },
  { href: "/audit", label: "Audit Feed" },
  { href: "/demo", label: "Demo" },
  { href: "/docs", label: "Docs" },
] as const;

export function Header() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-bg-3 bg-bg-1">
      <div className="mx-auto flex h-12 max-w-screen-2xl items-center gap-6 px-4">
        {/* Wordmark */}
        <Link
          href="/"
          className="shrink-0 font-mono text-sm font-semibold tracking-tight text-fg-0"
        >
          SECURECLAIM AI
          <span className="mx-1 text-fg-3">/</span>
          <span className="text-fg-2">Resilience Console</span>
        </Link>

        {/* Nav */}
        <nav className="flex items-center gap-1 overflow-x-auto">
          {NAV_LINKS.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "shrink-0 rounded px-2.5 py-1 font-mono text-xs text-fg-2",
                "transition-colors hover:bg-bg-2 hover:text-fg-0",
                "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              )}
            >
              {label}
            </Link>
          ))}
        </nav>

        {/* Right-side controls */}
        <div className="ml-auto flex items-center gap-3">
          {/* System status — static placeholder for scaffold */}
          <span
            className="hidden items-center gap-2 font-mono text-xs text-fg-2 sm:flex"
            aria-label="System status"
          >
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-ok" />
            <span>
              Attacks today: <span className="text-fg-1">—</span>
              {"  "}·{"  "}Blocked: <span className="text-fg-1">—</span>
              {"  "}·{"  "}Successful: <span className="text-ok">0</span>
            </span>
          </span>

          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub repository"
            className={cn(
              "rounded p-1.5 text-fg-2 transition-colors",
              "hover:bg-bg-2 hover:text-fg-0",
              "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            )}
          >
            <ExternalLink size={16} />
          </a>
        </div>
      </div>
    </header>
  );
}
