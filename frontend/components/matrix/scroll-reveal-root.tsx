"use client";

import { useEffect, useRef } from "react";
import type { ReactNode } from "react";

/**
 * Wraps page content and wires up the shared scroll-reveal pattern used by
 * the redesign: adds data-anim="on" to the root (unless the visitor prefers
 * reduced motion), then observes every descendant [data-rv] element and
 * flips on data-in the first time it scrolls into view. Mirrors the design
 * prototype's own componentDidMount logic.
 */
export function ScrollRevealRoot({
  children,
  style,
  ...rest
}: { children: ReactNode; style?: React.CSSProperties } & React.HTMLAttributes<HTMLDivElement>) {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    try {
      const reduce =
        window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if ("IntersectionObserver" in window && !reduce) {
        root.setAttribute("data-anim", "on");
        const io = new IntersectionObserver(
          (entries) => {
            entries.forEach((entry) => {
              if (entry.isIntersecting) {
                entry.target.setAttribute("data-in", "1");
                io.unobserve(entry.target);
              }
            });
          },
          { threshold: 0.02 }
        );
        root.querySelectorAll("[data-rv]").forEach((el) => io.observe(el));
        return () => io.disconnect();
      }
    } catch {
      /* no-op */
    }
  }, []);

  return (
    <div ref={rootRef} data-page="matrix" style={style} {...rest}>
      {children}
    </div>
  );
}
