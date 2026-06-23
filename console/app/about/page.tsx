import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "About — SecureClaim AI",
  description:
    "Built by Athish G R as a portfolio artifact demonstrating resilient agentic AI architecture against a curated 79-category attack taxonomy.",
};

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-screen-2xl px-4 py-16">
      <h1 className="font-mono text-lg font-semibold text-fg-0">About</h1>
    </div>
  );
}
