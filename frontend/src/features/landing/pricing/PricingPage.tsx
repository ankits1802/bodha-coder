import type { PlanCatalog } from "@/lib/api/types";
import styles from "../landing.module.css";
import { LandingNav } from "../LandingNav";
import { PricingPlans } from "./PricingPlans";
import { PricingStructuredData } from "./PricingStructuredData";
import { PRICING_TEXT } from "./strings";

export function PricingPage({ catalog }: { catalog: PlanCatalog | null }) {
  return (
    <div className={`${styles.root} min-h-screen bg-surface text-body-lg text-label`}>
      {catalog ? <PricingStructuredData catalog={catalog} /> : null}
      <LandingNav sectionBase="/" />
      <main className="px-6 pt-20 pb-28 sm:pt-28">
        <div className="mx-auto flex max-w-landing flex-col items-center gap-10">
          <header className="flex flex-col items-center gap-4 text-center">
            <h1 className="m-0 font-display text-hero-sm font-bold tracking-display sm:text-display">{PRICING_TEXT.title}</h1>
            <p className="m-0 max-w-160 text-title3 text-secondary">{PRICING_TEXT.lead}</p>
          </header>
          <PricingPlans catalog={catalog} />
        </div>
      </main>
    </div>
  );
}
