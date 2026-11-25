import Link from "next/link";
import { DemoRequestButton } from "./DemoRequestButton";
import { HowItWorks } from "./HowItWorks";
import { LandingFooter } from "./LandingFooter";
import { LandingNav } from "./LandingNav";
import { ProductShot } from "./ProductShot";
import { SecuritySection } from "./SecuritySection";
import { LANDING_TEXT } from "./strings";

function Hero() {
  const words = LANDING_TEXT.hero;
  return (
    <section className="flex flex-col items-center gap-5.5 px-6 pt-28 pb-16 text-center">
      <h1 className="m-0 max-w-225 font-display text-display font-bold tracking-display sm:text-display-lg lg:text-hero">
        {words.title}
      </h1>
      <p className="m-0 max-w-160 text-title3 text-secondary sm:text-title">{words.lead}</p>
      <div className="mt-2.5 flex flex-wrap items-center justify-center gap-3.5">
        <DemoRequestButton />
        <Link href="/sign-in" className="text-headline tracking-snug text-label hover:underline">
          {words.signIn}
        </Link>
      </div>
    </section>
  );
}

export function LandingPage() {
  return (
    <div className="min-h-screen bg-surface text-body-lg text-label">
      <LandingNav />
      <main>
        <Hero />
        <ProductShot />
        <HowItWorks />
        <SecuritySection />
        <LandingFooter />
      </main>
    </div>
  );
}
