import type { PlanCatalog } from "@/lib/api/types";
import { Bento } from "./bento/Bento";
import { ClosingCta } from "./ClosingCta";
import { Desks } from "./desks/Desks";
import { Faq } from "./faq/Faq";
import { Workflow } from "./flow/Workflow";
import { FloatingProduct } from "./hero/FloatingProduct";
import { Hero } from "./hero/Hero";
import styles from "./landing.module.css";
import { LandingFooter } from "./LandingFooter";
import { LandingNav } from "./LandingNav";
import { MotionRoot } from "./motion/MotionRoot";
import { PricingTeaser } from "./pricing/PricingTeaser";
import { SampleReview } from "./sample/SampleReview";
import { Numbers } from "./sections/Numbers";
import { SecuritySection } from "./SecuritySection";
import { Story } from "./story/Story";
import { Worth } from "./worth/Worth";

export function LandingPage({ catalog }: { catalog: PlanCatalog | null }) {
  return (
    <MotionRoot className={`${styles.root} min-h-screen bg-surface text-body-lg text-label`}>
      <LandingNav />
      <main>
        <Hero />
        <FloatingProduct />
        <Story />
        <SampleReview />
        <Numbers />
        <Desks />
        <Bento />
        <Worth />
        <Workflow />
        <SecuritySection />
        <PricingTeaser catalog={catalog} />
        <Faq />
        <ClosingCta />
      </main>
      <LandingFooter />
    </MotionRoot>
  );
}
