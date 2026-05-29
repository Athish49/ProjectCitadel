import { ATTACKS, toMatrixRow } from "@/lib/data/attacks";
import { MatrixShell } from "@/components/matrix/matrix-shell";
import type { MatrixClass, AttackCategory, PatternId } from "@/lib/types/showcase";

interface PageProps {
  searchParams: Promise<{ class?: string; pattern?: string; category?: string }>;
}

export default async function MatrixPage({ searchParams }: PageProps) {
  const { class: cls, pattern, category } = await searchParams;
  const rows = ATTACKS.map(toMatrixRow);

  const VALID_CLASSES: MatrixClass[]    = ["LIVE", "ARCHITECTURAL", "OUT-OF-SCOPE"];
  const VALID_PATTERNS: PatternId[]     = ["P1","P2","P3","P4","P5","P6","P7","P8","P9","P10","P11","P12"];

  const initialClass    = VALID_CLASSES.includes(cls as MatrixClass)     ? (cls as MatrixClass)    : null;
  const initialPattern  = VALID_PATTERNS.includes(pattern as PatternId)  ? (pattern as PatternId)  : null;
  const initialCategory = category ? (decodeURIComponent(category) as AttackCategory) : null;

  return (
    <MatrixShell
      rows={rows}
      initialClass={initialClass}
      initialPattern={initialPattern}
      initialCategory={initialCategory}
    />
  );
}
