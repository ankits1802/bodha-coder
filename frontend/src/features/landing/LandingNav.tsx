import Link from "next/link";
import { SHARED_TEXT } from "@/components/shared/strings";
import { DemoRequestButton } from "./DemoRequestButton";
import styles from "./landing.module.css";
import { NavShell } from "./motion/NavShell";
import { LANDING_TEXT } from "./strings";

export function LandingNav() {
  const words = LANDING_TEXT.nav;
  return (
    <NavShell label={words.label} className={styles.nav}>
      <div className="mx-auto flex min-h-13 max-w-landing items-center justify-between gap-4 px-6 py-2">
        <Link href="/" className="text-input font-semibold tracking-snug text-label">
          {SHARED_TEXT.brand}
        </Link>
        <div className="flex items-center gap-5 text-callout text-label-soft sm:gap-6.5">
          <a href="#how" className={`hidden hover:text-label sm:inline ${styles.link}`}>
            {words.how}
          </a>
          <a href="#security" className={`hidden hover:text-label sm:inline ${styles.link}`}>
            {words.security}
          </a>
          <Link href="/sign-in" className={`hover:text-label ${styles.link}`}>
            {words.signIn}
          </Link>
          <DemoRequestButton size="sm" />
        </div>
      </div>
    </NavShell>
  );
}
