import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Claim Demo — SecureClaim AI",
  description:
    "Walk through a live happy-path insurance claim and customer inquiry to see the security pipeline in action end to end.",
};

export default function DemoPage() {
  return (
    <div className="mx-auto max-w-screen-2xl px-4 py-16">
      <h1 className="font-mono text-lg font-semibold text-fg-0">Claim &amp; Inquiry Demo</h1>
    </div>
  );
}
