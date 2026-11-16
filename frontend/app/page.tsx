import { Nav } from "@/components/layout/nav";
import { Footer } from "@/components/layout/footer";
import { HomeAnimRoot } from "@/components/home/scroll-reveal";
import { HeroSection } from "@/components/home/hero";
import { ArchitectureSection } from "@/components/home/architecture-section";
import { PlaygroundTeaser } from "@/components/home/playground-teaser";
import { PatternsSection } from "@/components/home/patterns-section";
import { MatrixSection } from "@/components/home/matrix-section";
import { AdversarySection } from "@/components/home/adversary-section";
import { VerificationRiskSection } from "@/components/home/verification-risk-section";
import { FinalCTA } from "@/components/home/final-cta";

export default function HomePage() {
  return (
    <div style={{ minHeight: "100vh" }}>
      <Nav />
      <HomeAnimRoot>
        <main>
          <HeroSection />
          <ArchitectureSection />
          <PlaygroundTeaser />
          <PatternsSection />
          <MatrixSection />
          <AdversarySection />
          <VerificationRiskSection />
          <FinalCTA />
        </main>
      </HomeAnimRoot>
      <Footer />
    </div>
  );
}
