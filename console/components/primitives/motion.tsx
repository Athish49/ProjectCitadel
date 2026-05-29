"use client";

import { motion, type HTMLMotionProps } from "framer-motion";

// FadeIn — simple opacity entrance
export function FadeIn({
  children,
  delay = 0,
  duration = 0.4,
  ...props
}: HTMLMotionProps<"div"> & { delay?: number; duration?: number }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration, delay, ease: "easeOut" }}
      {...props}
    >
      {children}
    </motion.div>
  );
}

// SlideIn — translates up 12px while fading in; 200ms cubic-bezier per Doc 06 §4.4
export function SlideIn({
  children,
  delay = 0,
  direction = "up",
  ...props
}: HTMLMotionProps<"div"> & { delay?: number; direction?: "up" | "down" | "left" | "right" }) {
  const offsets: Record<string, { x: number; y: number }> = {
    up:    { x: 0,   y: 12  },
    down:  { x: 0,   y: -12 },
    left:  { x: 12,  y: 0   },
    right: { x: -12, y: 0   },
  };
  const { x, y } = offsets[direction];

  return (
    <motion.div
      initial={{ opacity: 0, x, y }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{ duration: 0.2, delay, ease: [0.4, 0, 0.2, 1] }}
      {...props}
    >
      {children}
    </motion.div>
  );
}

// Pulse — slow 2s pulse for live indicators (status dots, streaming badges)
export function Pulse({
  children,
  ...props
}: HTMLMotionProps<"span">) {
  return (
    <motion.span
      animate={{ opacity: [1, 0.35, 1] }}
      transition={{ duration: 2, ease: "easeInOut", repeat: Infinity }}
      {...props}
    >
      {children}
    </motion.span>
  );
}
