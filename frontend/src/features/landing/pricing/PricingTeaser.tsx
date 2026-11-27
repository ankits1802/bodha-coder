import { ButtonLink } from "@/components/ui/ButtonLink";
import type { PlanCatalog } from "@/lib/api/types";
import { cssVars } from "../motion/cssVars";
import { PRICING_PATH, PRICING_TEXT } from "./strings";
import { TeaserPlans } from "./TeaserPlans";

export function PricingTeaser({ catalog }: { catalog: PlanCatalog | null }) {
  const words = PRICING_TEXT.teaser;
  return (
    <section aria-labelledby="pricing-teaser-title" className="bg-muted-panel px-6 py-20 sm:py-24">
      <div className="mx-auto grid max-w-landing items-center gap-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:gap-14">
        <div className="flex min-w-0 flex-col items-start gap-4">
          <h2 id="pricing-teaser-title" data-reveal="" className="m-0 font-display text-hero-sm font-bold tracking-display sm:text-display">
            {words.title.map((line, index) => (
              <span key={line} className="block">
                {index > 0 ? ` ${line}` : line}
              </span>
            ))}
          </h2>
          <p data-reveal="" style={cssVars({ "--delay": "80ms" })} className="m-0 max-w-110 text-title3 text-secondary">
            {PRICING_TEXT.lead}
          </p>
          <div data-reveal="" style={cssVars({ "--delay": "160ms" })} className="mt-2">
            <ButtonLink href={PRICING_PATH} size="md">
              {words.more}
              <span aria-hidden="true">›</span>
            </ButtonLink>
          </div>
        </div>
        <TeaserPlans catalog={catalog} />
      </div>
    </section>
  );
}
