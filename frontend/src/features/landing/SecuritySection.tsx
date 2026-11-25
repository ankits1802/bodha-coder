import { LANDING_TEXT } from "./strings";

function CheckCircle() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true" className="flex-none text-ok">
      <circle cx="11" cy="11" r="11" fill="currentColor" />
      <path d="M6.5 11.3l3 3 6-6.3" fill="none" stroke="var(--color-white)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function SecuritySection() {
  const words = LANDING_TEXT.security;
  return (
    <section id="security" className="scroll-mt-16 px-6 py-30">
      <div className="mx-auto flex max-w-landing flex-wrap items-center justify-between gap-12">
        <div className="min-w-0 flex-[1_1_26rem]">
          <h2 className="m-0 font-display text-hero-sm font-bold tracking-display sm:text-display">{words.title}</h2>
          <p className="mt-4 mb-0 max-w-115 text-title3 text-secondary">{words.lead}</p>
        </div>
        <ul className="m-0 flex min-w-0 flex-[1_1_26rem] list-none flex-col gap-4.5 p-0">
          {words.items.map((item) => (
            <li key={item} className="flex items-center gap-3 text-headline tracking-snug">
              <CheckCircle />
              {item}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
