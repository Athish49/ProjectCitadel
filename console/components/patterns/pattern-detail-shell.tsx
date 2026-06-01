"use client";

import Link from "next/link";
import { ExternalLink, ArrowLeft } from "lucide-react";
import { FadeIn, SlideIn } from "@/components/primitives/motion";
import { CodeBlock } from "@/components/primitives/code-block";
import { PatternDiagram } from "./pattern-diagram";
import { cn } from "@/lib/utils";
import type { Pattern, CodeRef } from "@/lib/types/showcase";
import type { PatternExtra } from "@/lib/data/pattern-extras";

const GITHUB_BASE = "https://github.com/Athish49/ProjectCitadel/blob/main/";

function githubHref(ref: CodeRef): string {
  const base = GITHUB_BASE + ref.path;
  if (ref.lineStart) {
    return ref.lineEnd ? `${base}#L${ref.lineStart}-L${ref.lineEnd}` : `${base}#L${ref.lineStart}`;
  }
  return base;
}

interface SectionProps {
  title: string;
  children: React.ReactNode;
  className?: string;
}

function Section({ title, children, className }: SectionProps) {
  return (
    <section className={cn("border-t border-bg-3 pt-8", className)}>
      <h2 className="mb-4 font-mono text-xs font-semibold uppercase tracking-widest text-fg-3">
        {title}
      </h2>
      {children}
    </section>
  );
}

interface PatternDetailShellProps {
  pattern: Pattern;
  extra: PatternExtra;
}

export function PatternDetailShell({ pattern, extra }: PatternDetailShellProps) {
  return (
    <FadeIn className="mx-auto max-w-3xl px-4 py-10">
      {/* Back nav */}
      <Link
        href="/patterns"
        className="mb-8 inline-flex items-center gap-2 font-mono text-xs text-fg-3 transition-colors hover:text-fg-1"
      >
        <ArrowLeft size={12} />
        Defense Pattern Library
      </Link>

      {/* Hero */}
      <SlideIn>
        <div className="flex items-start justify-between gap-4">
          <div>
            <span className="font-mono text-sm font-semibold text-fg-3">{pattern.id}</span>
            <h1 className="mt-1 font-mono text-xl font-semibold text-fg-0">{pattern.name}</h1>
          </div>
          {pattern.testCount > 0 && (
            <span className="shrink-0 rounded border border-ok/20 bg-ok/5 px-2 py-1 font-mono text-sm text-ok">
              {pattern.testCount} tests passing
            </span>
          )}
        </div>
        <p className="mt-3 font-mono text-sm leading-relaxed text-fg-2">{pattern.summary}</p>
      </SlideIn>

      {/* Defends */}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <span className="font-mono text-xs text-fg-3">Defends attacks:</span>
        {pattern.attackIds.map((id) => (
          <Link
            key={id}
            href={`/matrix?pattern=${pattern.id}`}
            className="rounded border border-bg-3 px-1.5 py-0.5 font-mono text-xs text-fg-3 transition-colors hover:border-alert/40 hover:text-alert"
          >
            #{id}
          </Link>
        ))}
      </div>

      {/* Problem */}
      <Section title="Problem">
        <p className="font-mono text-sm leading-loose text-fg-2 whitespace-pre-line">
          {extra.problem.trim()}
        </p>
      </Section>

      {/* Pattern diagram */}
      <Section title="Pattern">
        <div className="mb-6 overflow-hidden rounded border border-bg-3">
          <PatternDiagram id={pattern.id} className="h-[160px] w-full" />
        </div>
        <div
          className="font-mono text-sm leading-loose text-fg-2 [&_strong]:text-fg-0 [&_code]:rounded [&_code]:bg-bg-2 [&_code]:px-1 [&_code]:text-xs [&_code]:text-fg-1"
          dangerouslySetInnerHTML={{ __html: pattern.description.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\n/g, "<br />") }}
        />
      </Section>

      {/* Implementation */}
      <Section title="Implementation">
        <CodeBlock
          code={extra.codeSnippet.trim()}
          lang={extra.codeLang}
          filename={extra.codeFilename}
          githubHref={GITHUB_BASE + extra.codeFilename}
          copyable
          className="mb-4"
        />
        {pattern.codeRefs.length > 0 && (
          <div className="mt-4 space-y-1">
            <p className="mb-2 font-mono text-xs text-fg-3">All code references:</p>
            {pattern.codeRefs.map((ref, i) => (
              <a
                key={i}
                href={githubHref(ref)}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 rounded px-2 py-1.5 font-mono text-xs transition-colors hover:bg-bg-2"
              >
                <span className="text-fg-2">{ref.label}</span>
                <span className="flex-1 text-fg-3">{ref.path}{ref.lineStart ? `:${ref.lineStart}` : ""}</span>
                <ExternalLink size={10} className="shrink-0 text-fg-3" />
              </a>
            ))}
          </div>
        )}
      </Section>

      {/* References */}
      <Section title="References">
        <ul className="space-y-3">
          {extra.references.map((ref, i) => (
            <li key={i} className="flex flex-col gap-0.5">
              <a
                href={ref.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 font-mono text-xs text-fg-1 underline underline-offset-2 transition-colors hover:text-fg-0"
              >
                {ref.label}
                <ExternalLink size={10} className="shrink-0 text-fg-3" />
              </a>
              {ref.note && (
                <span className="font-mono text-xs text-fg-3 pl-0">{ref.note}</span>
              )}
            </li>
          ))}
        </ul>
      </Section>

      {/* Residual Risk */}
      <Section title="Residual Risk">
        <div className="rounded border border-warn/20 bg-warn/5 p-4">
          <p className="font-mono text-sm leading-loose text-fg-2 whitespace-pre-line">
            {extra.residualRisk.trim()}
          </p>
        </div>
      </Section>

      {/* Compare */}
      <Section title="Without This Pattern">
        <div className="rounded border border-alert/20 bg-alert/5 p-4">
          <p className="font-mono text-sm leading-loose text-fg-2 whitespace-pre-line">
            {extra.compare.trim()}
          </p>
        </div>
        <p className="mt-3 font-mono text-xs text-fg-3">
          See live attack attempts in the{" "}
          <Link href={`/matrix?pattern=${pattern.id}`} className="text-fg-2 underline underline-offset-2 hover:text-fg-0">
            Threat Matrix →
          </Link>
        </p>
      </Section>

      {/* Bottom padding */}
      <div className="h-16" />
    </FadeIn>
  );
}
