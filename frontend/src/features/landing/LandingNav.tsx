import Link from "next/link";
import { SHARED_TEXT } from "@/components/shared/strings";
import { DemoRequestButton } from "./DemoRequestButton";
import { LANDING_TEXT } from "./strings";

export function LandingNav() {
  const words = LANDING_TEXT.nav;
  return (
    <nav aria-label={words.label} className="sticky top-0 z-10 border-b border-separator bg-surface/90 backdrop-blur">
      <div className="mx-auto flex min-h-13 max-w-landing flex-wrap items-center justify-between gap-4 px-6 py-2">
        <Link href="/" className="text-input font-semibold tracking-snug text-label">
          {SHARED_TEXT.brand}
        </Link>
        <div className="flex flex-wrap items-center gap-6.5 text-callout text-label-soft">
          <a href="#how" className="hover:text-label">
            {words.how}
          </a>
          <a href="#security" className="hover:text-label">
            {words.security}
          </a>
          <Link href="/sign-in" className="hover:text-label">
            {words.signIn}
          </Link>
          <DemoRequestButton size="sm" />
        </div>
      </div>
    </nav>
  );
}
