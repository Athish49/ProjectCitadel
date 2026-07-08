"use client";

import { motion, type MotionProps } from "framer-motion";
import type { ReactNode, CSSProperties } from "react";

interface RevealProps extends MotionProps {
  children: ReactNode;
  style?: CSSProperties;
  className?: string;
  delay?: number;
  as?: keyof typeof motion;
}

export function Reveal({ children, style, className, delay = 0, ...rest }: RevealProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1], delay }}
      viewport={{ once: true, amount: 0.12 }}
      style={style}
      className={className}
      {...rest}
    >
      {children}
    </motion.div>
  );
}
