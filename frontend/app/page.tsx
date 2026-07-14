import { Nav } from "@/components/layout/nav";
import { Footer } from "@/components/layout/footer";
import { HeroSection } from "@/components/home/hero";
import { ArchitectureSection } from "@/components/home/architecture-section";
import { PlaygroundTeaser } from "@/components/home/playground-teaser";
import { PatternsSection } from "@/components/home/patterns-section";
import { MatrixSection } from "@/components/home/matrix-section";
import { AdversarySection } from "@/components/home/adversary-section";
import { VerificationSection } from "@/components/home/verification-section";
import { RisksSection } from "@/components/home/risks-section";
import { FinalCTA } from "@/components/home/final-cta";

export default function HomePage() {
  return (
    <div style={{ minHeight: "100vh", background: "#0A0B0C" }}>
      <Nav />
      <HeroSection />
      <ArchitectureSection />
      <PlaygroundTeaser />
      <PatternsSection />
      <MatrixSection />
      <AdversarySection />
      <VerificationSection />
      <RisksSection />
      <FinalCTA />
      <Footer />
    </div>
  );
}
