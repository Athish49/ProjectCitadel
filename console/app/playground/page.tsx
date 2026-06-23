import type { Metadata } from "next";
import { PlaygroundShell } from "@/components/playground/playground-shell";

export const metadata: Metadata = {
  title: "Attack Playground — SecureClaim AI",
  description:
    "Fire attacks from the 79-category taxonomy and watch the defense layers respond in real time. Layer-by-layer trace with linked audit evidence.",
};
import type { AttackComposerTab } from "@/lib/types/playground";

const VALID_TABS: AttackComposerTab[] = ["chat", "pdf", "image", "tool", "cross-customer", "custom"];

interface PageProps {
  searchParams: Promise<{ template?: string; tab?: string; autorun?: string }>;
}

export default async function PlaygroundPage({ searchParams }: PageProps) {
  const { template, tab, autorun } = await searchParams;
  const initialTab = VALID_TABS.includes(tab as AttackComposerTab)
    ? (tab as AttackComposerTab)
    : null;

  return (
    <PlaygroundShell
      initialTemplateId={template ?? null}
      initialTab={initialTab}
      autorun={autorun === "1"}
    />
  );
}
