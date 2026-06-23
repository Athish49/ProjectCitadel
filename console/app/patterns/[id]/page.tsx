import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { PATTERNS, getPattern } from "@/lib/data/patterns";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const pattern = getPattern(id.toUpperCase() as import("@/lib/types/showcase").PatternId);
  if (!pattern) return {};
  return {
    title: `${pattern.id} — ${pattern.name} — SecureClaim AI`,
    description: pattern.summary,
  };
}
import { PATTERN_EXTRAS } from "@/lib/data/pattern-extras";
import { PatternDetailShell } from "@/components/patterns/pattern-detail-shell";
import type { PatternId } from "@/lib/types/showcase";

export function generateStaticParams() {
  return PATTERNS.map((p) => ({ id: p.id.toLowerCase() }));
}

export default async function PatternDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const patternId = id.toUpperCase() as PatternId;
  const pattern = getPattern(patternId);
  if (!pattern) notFound();

  const extra = PATTERN_EXTRAS[patternId];
  if (!extra) notFound();

  return <PatternDetailShell pattern={pattern} extra={extra} />;
}
