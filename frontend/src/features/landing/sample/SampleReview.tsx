import { Magnetic } from "../motion/Magnetic";
import { cssVars } from "../motion/cssVars";
import { StartTrialButton } from "../StartTrialButton";
import { LANDING_TEXT } from "../strings";
import { SampleTabs } from "./SampleTabs";
import { SAMPLE_NOTES } from "./samples";
import { SAMPLE_TEXT } from "./strings";

export function SampleReview() {
  return (
    <section aria-labelledby="sample-title" className="px-6 py-28 sm:py-32">
      <div className="mx-auto max-w-landing">
        <h2 id="sample-title" data-reveal="" className="m-0 text-center font-display text-hero-sm font-bold tracking-display sm:text-display">
          {SAMPLE_TEXT.title}
        </h2>
        <div data-reveal="" className="mt-10" style={cssVars({ "--delay": "80ms" })}>
          <SampleTabs label={SAMPLE_TEXT.tabsLabel} samples={SAMPLE_NOTES} />
        </div>
        <div data-reveal="" className="mt-12 flex justify-center">
          <Magnetic>
            <StartTrialButton label={LANDING_TEXT.startTrial} />
          </Magnetic>
        </div>
      </div>
    </section>
  );
}
