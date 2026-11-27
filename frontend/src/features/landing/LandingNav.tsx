import Link from "next/link";
import { SHARED_TEXT } from "@/components/shared/strings";
import { NAV_SECTIONS, sectionHref } from "./anchors";
import styles from "./landing.module.css";
import { NavShell } from "./motion/NavShell";
import { SectionMenu } from "./nav/SectionMenu";
import { PRICING_PATH, PRICING_TEXT } from "./pricing/strings";
import { StartTrialButton } from "./StartTrialButton";
import { LANDING_TEXT } from "./strings";

export function LandingNav({ sectionBase = "" }: { sectionBase?: string }) {
  const words = LANDING_TEXT.nav;
  const links = NAV_SECTIONS.map((key) => ({ href: `${sectionBase}${sectionHref(key)}`, label: LANDING_TEXT.sections[key] }));
  const menuLinks = [...links, { href: PRICING_PATH, label: PRICING_TEXT.nav }, { href: "/sign-in", label: words.signIn }];
  return (
    <NavShell label={words.label} className={styles.nav}>
      <div className="mx-auto flex min-h-13 max-w-landing items-center justify-between gap-4 px-6 py-2">
        <Link href="/" className="text-input font-semibold tracking-snug whitespace-nowrap text-label">
          {SHARED_TEXT.brand}
        </Link>
        <ul className="m-0 hidden list-none items-center gap-6.5 p-0 text-callout text-label-soft lg:flex">
          {links.map((link) => (
            <li key={link.href}>
              <a href={link.href} className={`hover:text-label ${styles.link}`}>
                {link.label}
              </a>
            </li>
          ))}
          <li>
            <Link href={PRICING_PATH} className={`hover:text-label ${styles.link}`}>
              {PRICING_TEXT.nav}
            </Link>
          </li>
        </ul>
        <div className="flex items-center gap-4 text-callout text-label-soft sm:gap-6.5">
          <Link href="/sign-in" className={`hidden whitespace-nowrap hover:text-label min-[360px]:inline ${styles.link}`}>
            {words.signIn}
          </Link>
          <StartTrialButton size="sm" label={words.startFree} />
          <SectionMenu label={words.sections} links={menuLinks} />
        </div>
      </div>
    </NavShell>
  );
}
