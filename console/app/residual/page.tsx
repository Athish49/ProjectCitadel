"use client";

import Link from "next/link";
import { RESIDUAL_RISKS, type RiskStatus } from "@/lib/data/residual-risks";
import { cn } from "@/lib/utils";

const STATUS_STYLES: Record<RiskStatus, string> = {
  accepted: "bg-warn/10 text-warn border border-warn/30",
  planned: "bg-blue-500/10 text-blue-400 border border-blue-500/30",
  "won't-do": "bg-fg-3/10 text-fg-3 border border-fg-3/20",
};

const STATUS_LABELS: Record<RiskStatus, string> = {
  accepted: "accepted",
  planned: "planned",
  "won't-do": "won't-do",
};

export default function ResidualPage() {
  const accepted = RESIDUAL_RISKS.filter((r) => r.status === "accepted").length;
  const planned = RESIDUAL_RISKS.filter((r) => r.status === "planned").length;
  const wontDo = RESIDUAL_RISKS.filter((r) => r.status === "won't-do").length;

  return (
    <div className="mx-auto max-w-screen-xl px-4 py-10">
      {/* Header */}
      <div className="mb-2">
        <h1 className="font-mono text-lg font-semibold text-fg-0">
          Residual Risk Register
        </h1>
        <p className="mt-1 font-mono text-sm text-fg-3">
          {RESIDUAL_RISKS.length} risks documented ·{" "}
          <span className="text-warn">{accepted} accepted</span>
          {" · "}
          <span className="text-blue-400">{planned} planned</span>
          {" · "}
          <span className="text-fg-3">{wontDo} won&apos;t-do</span>
        </p>
      </div>

      <p className="mb-8 max-w-2xl font-mono text-xs text-fg-3">
        Risks that remain after all implemented controls. Each entry documents
        the residual exposure, why it was not fully eliminated, and the
        production mitigation in place. Accepted risks are acknowledged and
        tracked. Planned items have committed remediation work. Won&apos;t-do
        items are out of scope by design.
      </p>

      {/* Risk cards */}
      <div className="flex flex-col gap-4">
        {RESIDUAL_RISKS.map((risk) => (
          <div
            key={risk.id}
            className="rounded-lg border border-bg-3 bg-bg-1 p-5"
          >
            {/* Top row */}
            <div className="mb-3 flex flex-wrap items-start gap-3">
              <span className="shrink-0 font-mono text-xs text-fg-3">
                {risk.id}
              </span>
              <h2 className="flex-1 font-mono text-sm font-semibold text-fg-0">
                {risk.title}
              </h2>
              <span
                className={cn(
                  "shrink-0 rounded px-2 py-0.5 font-mono text-xs",
                  STATUS_STYLES[risk.status]
                )}
              >
                {STATUS_LABELS[risk.status]}
              </span>
            </div>

            {/* Pattern chips */}
            {risk.patternIds.length > 0 && (
              <div className="mb-3 flex flex-wrap gap-1.5">
                {risk.patternIds.map((pid) => (
                  <Link
                    key={pid}
                    href={`/patterns/${pid.toLowerCase()}`}
                    className="rounded bg-bg-2 px-2 py-0.5 font-mono text-xs text-fg-2 transition-colors hover:bg-bg-3 hover:text-fg-0"
                  >
                    {pid}
                  </Link>
                ))}
              </div>
            )}

            {/* Body */}
            <div className="grid gap-3 md:grid-cols-3">
              <div>
                <p className="mb-1 font-mono text-xs font-semibold uppercase tracking-widest text-fg-3">
                  Description
                </p>
                <p className="font-mono text-xs leading-relaxed text-fg-2">
                  {risk.description}
                </p>
              </div>
              <div>
                <p className="mb-1 font-mono text-xs font-semibold uppercase tracking-widest text-fg-3">
                  Why it remains
                </p>
                <p className="font-mono text-xs leading-relaxed text-fg-2">
                  {risk.whyItRemains}
                </p>
              </div>
              <div>
                <p className="mb-1 font-mono text-xs font-semibold uppercase tracking-widest text-fg-3">
                  Production mitigation
                </p>
                <p className="font-mono text-xs leading-relaxed text-fg-2">
                  {risk.productionMitigation}
                </p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Footer note */}
      <p className="mt-10 font-mono text-xs text-fg-3">
        This register is maintained alongside the codebase. See also{" "}
        <a
          href="https://github.com/Athish49/ProjectCitadel/blob/main/RESIDUAL_RISKS.md"
          target="_blank"
          rel="noopener noreferrer"
          className="text-fg-2 underline underline-offset-2 hover:text-fg-0"
        >
          RESIDUAL_RISKS.md
        </a>{" "}
        in the repository root. Cross-referenced patterns link to the{" "}
        <Link href="/patterns" className="text-fg-2 underline underline-offset-2 hover:text-fg-0">
          Defense Pattern Library
        </Link>
        .
      </p>
    </div>
  );
}
