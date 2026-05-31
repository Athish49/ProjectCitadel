import { readFileSync } from "fs";
import { join, resolve } from "path";
import { FormalShell } from "@/components/formal/formal-shell";
import type { CIResults } from "@/lib/types/showcase";

function loadTlaSpec(): string {
  try {
    return readFileSync(
      resolve(process.cwd(), "..", "backend", "formal", "workflow.tla"),
      "utf-8"
    );
  } catch {
    return "";
  }
}

function loadCI(): CIResults | null {
  try {
    const raw = readFileSync(
      join(process.cwd(), "public", "ci-test-results.json"),
      "utf-8"
    );
    return JSON.parse(raw) as CIResults;
  } catch {
    return null;
  }
}

export default function FormalPage() {
  const tlaSpec = loadTlaSpec();
  const ci = loadCI();

  return (
    <FormalShell
      tlaSpec={tlaSpec}
      checkedAt={ci?.timestamp ?? null}
      unitPassed={ci?.unit.passed ?? null}
      unitTotal={ci?.unit.total ?? null}
    />
  );
}
