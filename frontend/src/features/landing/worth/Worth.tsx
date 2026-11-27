import { SECTION_IDS } from "../anchors";
import { LANDING_TEXT } from "../strings";
import { Estimator } from "./Estimator";

export function Worth() {
  const words = LANDING_TEXT.worth;
  return (
    <section id={SECTION_IDS.worth} aria-labelledby="worth-title" className="scroll-mt-16 px-6 py-28 sm:py-32">
      <div className="mx-auto max-w-landing">
        <div className="mx-auto max-w-180 text-center">
          <h2 id="worth-title" data-reveal="" className="m-0 font-display text-hero-sm font-bold tracking-display sm:text-display">
            {words.title}
          </h2>
          <p data-reveal="" className="mt-4 mb-0 text-title3 text-secondary">
            {words.lead}
          </p>
        </div>
        <div data-reveal="" className="mt-12">
          <Estimator />
        </div>
      </div>
    </section>
  );
}
