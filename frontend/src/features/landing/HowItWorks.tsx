import { LANDING_TEXT } from "./strings";

const DISPLAY = "m-0 font-display font-bold tracking-display";

export function HowItWorks() {
  const { how, numbers } = LANDING_TEXT;
  return (
    <>
      <section id="how" className="scroll-mt-16 px-6 pb-30">
        <div className="mx-auto flex max-w-landing flex-col gap-12">
          <h2 className={`${DISPLAY} text-center text-hero-sm sm:text-display`}>{how.title}</h2>
          <div className="grid grid-cols-[repeat(auto-fit,minmax(18rem,1fr))] gap-5">
            {how.features.map((feature) => (
              <div key={feature.title} className="flex flex-col gap-2 rounded-feature bg-muted-panel px-8 py-9">
                <h3 className="m-0 text-title font-semibold tracking-title">{feature.title}</h3>
                <p className="m-0 text-headline leading-normal text-secondary">{feature.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
      <section aria-label={numbers.label} className="bg-muted-panel px-6 py-24">
        <div className="mx-auto grid max-w-landing grid-cols-[repeat(auto-fit,minmax(15rem,1fr))] gap-10 text-center">
          {numbers.items.map((item) => (
            <div key={item.label}>
              <div className={`${DISPLAY} text-display-lg tracking-tightest tabular-nums`}>{item.value}</div>
              <p className="mt-1.5 mb-0 text-headline text-secondary">{item.label}</p>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
