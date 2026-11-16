"use client";

import { useEffect, useRef, type ReactNode } from "react";

/**
 * Shared scroll-reveal system described in globals.css: on mount, unless the
 * visitor prefers reduced motion, mark the target `data-anim="on"` and
 * observe every descendant `[data-rv]`, flipping on `data-in` once it enters
 * the viewport. Ported from the design prototype's own componentDidMount.
 * Consolidates what were four near-identical per-page copies of this effect.
 */
function observeReveal(root: Element, threshold: number): (() => void) | undefined {
  try {
    const reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce || !("IntersectionObserver" in window)) return undefined;

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
      { threshold }
    );
    root.querySelectorAll("[data-rv]").forEach((el) => io.observe(el));
    return () => io.disconnect();
  } catch {
    return undefined;
  }
}

interface ScrollRevealProps {
  /** IntersectionObserver threshold — each page previously hardcoded its own
   * slightly different value (0.02–0.05); kept per-call-site so consolidating
   * this doesn't change any page's reveal timing. */
  threshold?: number;
}

/** No-wrapper variant — observes from `document.body`. */
export function ScrollReveal({ threshold = 0.05 }: ScrollRevealProps) {
  useEffect(() => {
    return observeReveal(document.body, threshold);
  }, [threshold]);

  return null;
}

interface ScrollRevealRootProps extends ScrollRevealProps, React.HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  dataPage?: string;
}

/** Wrapper variant — observes from a locally-ref'd root div instead of `document.body`. */
export function ScrollRevealRoot({ children, threshold = 0.05, dataPage, style, ...rest }: ScrollRevealRootProps) {
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    return observeReveal(root, threshold);
  }, [threshold]);

  return (
    <div ref={rootRef} data-page={dataPage} style={style} {...rest}>
      {children}
    </div>
  );
}
