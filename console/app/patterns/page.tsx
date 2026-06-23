import type { Metadata } from "next";
import { PATTERNS } from "@/lib/data/patterns";

export const metadata: Metadata = {
  title: "Defense Pattern Library — SecureClaim AI",
  description:
    "P1–P12: twelve architectural defense patterns with citations, implementation code, and animated diagrams. Named patterns, not regexes.",
};
import { PatternCard } from "@/components/patterns/pattern-card";

export default function PatternsPage() {
  return (
    <div className="mx-auto max-w-screen-2xl px-4 py-10">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-mono text-lg font-semibold text-fg-0">Defense Pattern Library</h1>
        <p className="mt-1 font-mono text-sm text-fg-3">
          {PATTERNS.length} architectural patterns · {PATTERNS.reduce((n, p) => n + p.testCount, 0)} test assertions · all implemented
        </p>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {PATTERNS.map((p) => (
          <PatternCard key={p.id} pattern={p} />
        ))}
      </div>
    </div>
  );
}
