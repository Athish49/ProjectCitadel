import type { Metadata } from "next";
import { Nav } from "@/components/layout/nav";
import { Footer } from "@/components/layout/footer";
import { AdversaryView } from "@/components/adversary/adversary-view";

export const metadata: Metadata = {
  title: "Adversarial Agent — Project Citadel",
};

export default function AdversaryPage() {
  return (
    <div style={{ minHeight: "100vh", background: "#0A0B0C" }}>
      <Nav />
      <main>
        <AdversaryView />
      </main>
      <Footer />
    </div>
  );
}
