"use client";

import { useEffect } from "react";

/**
 * Mirrors the design prototype's componentDidMount scroll-reveal behavior:
 * sets data-anim="on" on the page body (guarded by prefers-reduced-motion),
 * then observes every [data-rv] element and flips on data-in once it enters
 * view. Pairs with the [data-anim="on"] [data-rv] rules in globals.css.
 */
export function ScrollReveal() {
  useEffect(() => {
    try {
      const reduce =
        window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (reduce || !("IntersectionObserver" in window)) return;

      document.body.setAttribute("data-anim", "on");

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

      document.querySelectorAll("[data-rv]").forEach((el) => io.observe(el));

      return () => io.disconnect();
    } catch {
      /* no-op */
    }
  }, []);

  return null;
}
