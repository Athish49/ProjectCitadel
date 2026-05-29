import Link from "next/link";
import { ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";

interface EvidenceLinkProps {
  href: string;
  label: string;
  external?: boolean;
  className?: string;
}

export function EvidenceLink({ href, label, external = false, className }: EvidenceLinkProps) {
  const shared = cn(
    "inline-flex items-center gap-1 rounded-sm border border-trust/30 bg-trust/5 px-1.5 py-0.5",
    "font-mono text-[10px] text-trust/80 transition-colors hover:border-trust/60 hover:bg-trust/10 hover:text-trust",
    className
  );

  if (external) {
    return (
      <a href={href} target="_blank" rel="noopener noreferrer" className={shared}>
        {label}
        <ExternalLink className="h-2.5 w-2.5" aria-hidden />
      </a>
    );
  }

  return (
    <Link href={href} className={shared}>
      {label}
    </Link>
  );
}
