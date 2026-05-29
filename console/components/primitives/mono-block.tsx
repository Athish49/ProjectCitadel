import { cn } from "@/lib/utils";

type Severity = "ok" | "warn" | "alert" | "attack" | "trust" | "audit" | "neutral";

const SEVERITY_COLORS: Record<Severity, string> = {
  ok:      "text-ok",
  warn:    "text-warn",
  alert:   "text-alert",
  attack:  "text-attack",
  trust:   "text-trust",
  audit:   "text-audit",
  neutral: "text-fg-2",
};

const SEVERITY_DOT: Record<Severity, string> = {
  ok:      "bg-ok",
  warn:    "bg-warn",
  alert:   "bg-alert",
  attack:  "bg-attack",
  trust:   "bg-trust",
  audit:   "bg-audit",
  neutral: "bg-fg-3",
};

interface MonoBlockProps {
  timestamp?: string;
  severity?: Severity;
  label?: string;
  message: string;
  className?: string;
}

export function MonoBlock({
  timestamp,
  severity = "neutral",
  label,
  message,
  className,
}: MonoBlockProps) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded px-3 py-1.5 font-mono text-xs",
        "bg-bg-1 hover:bg-bg-2 transition-colors",
        className
      )}
    >
      {/* severity dot */}
      <span
        className={cn("mt-[3px] h-1.5 w-1.5 shrink-0 rounded-full", SEVERITY_DOT[severity])}
        aria-hidden
      />

      {/* timestamp */}
      {timestamp && (
        <span className="shrink-0 tabular-nums text-fg-3">{timestamp}</span>
      )}

      {/* label badge */}
      {label && (
        <span
          className={cn(
            "shrink-0 rounded-sm px-1 py-0.5 text-[10px] font-medium uppercase tracking-wide",
            SEVERITY_COLORS[severity],
            "border border-current opacity-70"
          )}
        >
          {label}
        </span>
      )}

      {/* message */}
      <span className="min-w-0 break-all text-fg-1">{message}</span>
    </div>
  );
}
