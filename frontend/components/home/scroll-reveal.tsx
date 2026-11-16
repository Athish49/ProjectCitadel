"use client";

import { useEffect, useRef, type ReactNode } from "react";

/**
 * Wraps the home page's main content and implements the shared scroll-reveal
 * system described in globals.css: on mount, if the visitor hasn't requested
 * reduced motion, mark this subtree `data-anim="on"` and observe every
 * descendant `[data-rv]` element, flipping on `data-in` as it enters the
 * viewport. Ported from Main.dc.html's own componentDidMount.
 */
export function HomeAnimRoot({ children }: { children: ReactNode }) {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    let reduce = false;
    try {
      reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    } catch {
      reduce = false;
    }

    if (reduce || !("IntersectionObserver" in window)) return;

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
      { threshold: 0.05 }
    );

    root.querySelectorAll("[data-rv]").forEach((el) => io.observe(el));

    return () => io.disconnect();
  }, []);

  return <div ref={rootRef}>{children}</div>;
}
