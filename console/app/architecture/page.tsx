import type { Metadata } from "next";
import { ArchDiagram } from "@/components/architecture/arch-diagram";

export const metadata: Metadata = {
  title: "Architecture Explorer — SecureClaim AI",
  description:
    "Interactive system diagram of the SecureClaim AI multi-agent pipeline. Click any node to inspect its spec, tools, and live traffic.",
};

export default function ArchitecturePage() {
  return <ArchDiagram />;
}
