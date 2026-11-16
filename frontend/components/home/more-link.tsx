import Link from "next/link";
import type { CSSProperties, ReactNode } from "react";

interface MoreLinkProps {
  href: string;
  external?: boolean;
  children: ReactNode;
  style?: CSSProperties;
  /** Mark this link as a scroll-reveal target (see scroll-reveal.tsx). */
  reveal?: boolean;
}

/** The "Full architecture →", "Open the full playground →"-style links,
 * with the arrow nudging right on hover (design's `.more:hover span`). */
export function MoreLink({ href, external, children, style, reveal }: MoreLinkProps) {
  const commonStyle: CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    gap: "8px",
    minHeight: "44px",
    fontSize: "14px",
    fontWeight: 500,
    color: "rgba(255,255,255,0.95)",
    textDecoration: "none",
    ...style,
  };

  const content = (
    <>
      {children}
      <span
        aria-hidden="true"
        className="group-hover:translate-x-1"
        style={{ display: "inline-block", transition: "transform 0.25s" }}
      >
        →
      </span>
    </>
  );

  if (external) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="more group"
        style={commonStyle}
        {...(reveal ? { "data-rv": "" } : {})}
      >
        {content}
      </a>
    );
  }

  return (
    <Link href={href} className="more group" style={commonStyle} {...(reveal ? { "data-rv": "" } : {})}>
      {content}
    </Link>
  );
}
