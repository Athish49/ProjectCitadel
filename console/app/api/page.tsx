import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "API Explorer — SecureClaim AI",
  description:
    "Browse and test the live /showcase REST API: attack-defense matrix, defense patterns, architecture metadata, and audit stream.",
};

export default function ApiExplorerPage() {
  return (
    <div className="mx-auto max-w-screen-2xl px-4 py-16">
      <h1 className="font-mono text-lg font-semibold text-fg-0">API Explorer</h1>
    </div>
  );
}
