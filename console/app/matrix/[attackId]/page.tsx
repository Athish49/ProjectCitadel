import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ attackId: string }>;
}): Promise<Metadata> {
  const { attackId } = await params;
  const { ATTACKS, toMatrixRow } = await import("@/lib/data/attacks");
  const id = parseInt(attackId, 10);
  const entry = ATTACKS.find((a) => a.attackId === id);
  if (!entry) return {};
  const row = toMatrixRow(entry);
  return {
    title: `#${row.attackId} ${row.name} — Attack Matrix — SecureClaim AI`,
    description: `${row.class} · ${row.patterns.join(", ")} · ${row.name}`,
  };
}
import { ArrowLeft, Play, ShieldCheck, Shield, AlertTriangle } from "lucide-react";
import { ATTACKS, toMatrixRow, getAttackCategory } from "@/lib/data/attacks";
import { PATTERNS } from "@/lib/data/patterns";
import { cn } from "@/lib/utils";
import type { MatrixClass, MatrixRow } from "@/lib/types/showcase";

const CLASS_CONFIG: Record<MatrixClass, {
  label: string;
  icon: React.FC<{ className?: string }>;
  color: string;
  border: string;
  bg: string;
  rationale: string;
}> = {
  LIVE: {
    label: "LIVE",
    icon: ShieldCheck,
    color: "text-[#4ADE80]",
    border: "border-[#4ADE80]/40",
    bg: "bg-[#4ADE80]/8",
    rationale: "Actively tested by the adversarial agent. The defense patterns listed below are exercised against real variant payloads on each CI run.",
  },
  ARCHITECTURAL: {
    label: "ARCHITECTURAL",
    icon: Shield,
    color: "text-[#5BB5F2]",
    border: "border-[#5BB5F2]/40",
    bg: "bg-[#5BB5F2]/8",
    rationale: "Structurally not applicable. The design eliminates this threat vector before it can manifest — there is no surface for the attack to target.",
  },
  "OUT-OF-SCOPE": {
    label: "OUT-OF-SCOPE",
    icon: AlertTriangle,
    color: "text-[#8B96A8]",
    border: "border-[#8B96A8]/30",
    bg: "bg-transparent",
    rationale: "Acknowledged but not claimed. This attack operates at a layer (model training, infrastructure, supply chain) that application-level defenses cannot address.",
  },
};

// Map attack IDs to playground template IDs where available.
const PLAYGROUND_TEMPLATES: Record<number, string> = {
  1: "t1-direct-override",
  2: "t2-pdf-indirect",
  4: "t4-dan-jailbreak",
  6: "t6-image-steganography",
  7: "t7-semantic-injection",
  20: "t20-rls-bypass",
  21: "t21-summarize-forward",
  25: "t25-url-exfil",
  28: "t28-cross-customer",
  29: "t29-tool-misuse",
  65: "t65-social-eng",
  66: "t66-social-eng-agent",
  78: "t78-prompt-extraction",
};

function DefenseStat({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="flex flex-col items-center rounded border border-[#1E2632] bg-[#0F141B] px-4 py-3">
      <span className={cn("font-mono text-xl font-bold tabular-nums", color ?? "text-[#E8EDF2]")}>{value}</span>
      <span className="mt-0.5 font-mono text-[9px] uppercase tracking-widest text-[#8B96A8]">{label}</span>
    </div>
  );
}

function fmt(ts: string | null): string {
  if (!ts) return "—";
  const diff = Date.now() - new Date(ts).getTime();
  const m = Math.floor(diff / 60_000);
  if (m < 60)   return `${m}m ago`;
  if (m < 1440) return `${Math.floor(m / 60)}h ago`;
  return `${Math.floor(m / 1440)}d ago`;
}

export default async function AttackDetailPage({
  params,
}: {
  params: Promise<{ attackId: string }>;
}) {
  const { attackId } = await params;
  const id = parseInt(attackId, 10);

  const entry = ATTACKS.find((a) => a.attackId === id);
  if (!entry) notFound();

  const row: MatrixRow = toMatrixRow(entry);
  const cfg = CLASS_CONFIG[row.class];
  const Icon = cfg.icon;
  const templateId = PLAYGROUND_TEMPLATES[id] ?? null;
  const category = getAttackCategory(id);

  // Pattern detail objects for the patterns this attack exercises.
  const patternDetails = row.patterns
    .map((pid) => PATTERNS.find((p) => p.id === pid))
    .filter(Boolean) as (typeof PATTERNS)[number][];

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      {/* back */}
      <Link
        href="/matrix"
        className="mb-6 inline-flex items-center gap-1.5 font-mono text-[11px] text-[#8B96A8] transition-colors hover:text-[#E8EDF2]"
      >
        <ArrowLeft className="h-3 w-3" />
        Attack-Defense Matrix
      </Link>

      {/* header */}
      <div className={cn("rounded border px-5 py-4 mb-6", cfg.border, cfg.bg)}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-[10px] tabular-nums text-[#8B96A8]">#{id}</span>
              <span className="font-mono text-[10px] text-[#8B96A8]">{category}</span>
            </div>
            <h1 className="font-mono text-base font-semibold text-[#E8EDF2]">{entry.name}</h1>
          </div>
          <span className={cn("flex items-center gap-1.5 rounded border px-2 py-1 font-mono text-[10px]", cfg.border, cfg.color)}>
            <Icon className="h-3 w-3" />
            {cfg.label}
          </span>
        </div>
      </div>

      {/* description */}
      <section className="mb-6">
        <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-[#8B96A8]">Description</div>
        <p className="font-mono text-[12px] leading-relaxed text-[#A8B4C0]">{entry.description}</p>
      </section>

      {/* class rationale */}
      <section className="mb-6 rounded border border-[#1E2632] bg-[#0F141B] px-4 py-3">
        <div className="mb-1 font-mono text-[10px] uppercase tracking-widest text-[#8B96A8]">Classification rationale</div>
        <p className="font-mono text-[11px] leading-relaxed text-[#A8B4C0]">{cfg.rationale}</p>
      </section>

      {/* live stats */}
      {row.class === "LIVE" && (
        <section className="mb-6">
          <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-[#8B96A8]">Test results</div>
          <div className="grid grid-cols-5 gap-2">
            <DefenseStat label="Variants"   value={(row.variantCount ?? 0).toLocaleString()} />
            <DefenseStat label="Blocked"    value={row.blockedCount}    color="text-[#4ADE80]" />
            <DefenseStat label="Partial"    value={row.partialCount || "—"} color="text-[#F5B056]" />
            <DefenseStat label="False +"    value={row.falsePositiveCount || "—"} />
            <DefenseStat label="Last Run"   value={fmt(row.lastTestedAt)} />
          </div>
        </section>
      )}

      {/* patterns */}
      {patternDetails.length > 0 && (
        <section className="mb-6">
          <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-[#8B96A8]">Defense patterns</div>
          <div className="space-y-2">
            {patternDetails.map((p) => (
              <Link
                key={p.id}
                href={`/patterns/${p.id}`}
                className="block rounded border border-[#1E2632] bg-[#0F141B] px-4 py-3 transition-colors hover:border-[#5BB5F2]/30 hover:bg-[#0F141B]"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="rounded border border-[#5BB5F2]/25 px-1.5 py-0.5 font-mono text-[10px] text-[#5BB5F2]/70">{p.id}</span>
                  <span className="font-mono text-[11px] font-medium text-[#E8EDF2]">{p.name}</span>
                </div>
                <p className="font-mono text-[10px] leading-relaxed text-[#8B96A8]">{p.summary}</p>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* try in playground */}
      {templateId && (
        <section className="mb-6">
          <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-[#8B96A8]">Replay in playground</div>
          <Link
            href={`/playground?template=${templateId}&autorun=1`}
            className="inline-flex items-center gap-2 rounded border border-[#4ADE80]/30 bg-[#4ADE80]/8 px-4 py-2.5 font-mono text-[11px] text-[#4ADE80] transition-colors hover:border-[#4ADE80]/60 hover:bg-[#4ADE80]/12"
          >
            <Play className="h-3 w-3" />
            Run scenario: {entry.name}
          </Link>
        </section>
      )}

      {/* other attacks in same category */}
      <section>
        <div className="mb-2 font-mono text-[10px] uppercase tracking-widest text-[#8B96A8]">Category: {category}</div>
        <Link
          href={`/matrix?class=LIVE&category=${encodeURIComponent(category)}`}
          className="font-mono text-[11px] text-[#5BB5F2] transition-colors hover:text-[#A8D8F8]"
        >
          View all {category} attacks in matrix →
        </Link>
      </section>
    </div>
  );
}
