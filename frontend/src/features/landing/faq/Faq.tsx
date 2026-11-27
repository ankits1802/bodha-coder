import { SECTION_IDS } from "../anchors";
import { LANDING_TEXT } from "../strings";
import { FaqList } from "./FaqList";

export function Faq() {
  const words = LANDING_TEXT.faq;
  return (
    <section id={SECTION_IDS.faq} aria-labelledby="faq-title" className="scroll-mt-16 border-t border-separator px-6 py-28 sm:py-32">
      <div className="mx-auto grid max-w-landing gap-10 lg:grid-cols-[minmax(0,0.75fr)_minmax(0,1.25fr)] lg:gap-16">
        <h2 id="faq-title" data-reveal="" className="m-0 font-display text-hero-sm font-bold tracking-display sm:text-display">
          {words.title}
        </h2>
        <div data-reveal="">
          <FaqList items={words.items} />
        </div>
      </div>
    </section>
  );
}
