import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Adversarial Agent Dashboard — SecureClaim AI",
  description:
    "Live feed of the autonomous attacker: attack attempts, breach counter, cost tracking, and strategy panel — all public and transparent.",
};

export default function AdversaryLayout({ children }: { children: ReactNode }) {
  return children;
}
