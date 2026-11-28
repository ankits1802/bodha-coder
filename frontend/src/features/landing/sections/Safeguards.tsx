import { cssVars } from "../motion/cssVars";
import { LANDING_TEXT } from "../strings";
import styles from "./sections.module.css";

function CheckCircle() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true" className={`flex-none text-ok ${styles.check}`}>
      <circle cx="11" cy="11" r="11" fill="currentColor" />
      <path d="M6.5 11.3l3 3 6-6.3" pathLength={1} fill="none" className="stroke-white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Safeguards() {
  const items = LANDING_TEXT.security.items;
  return (
    <ul className={styles.safeguards}>
      {items.map((item, index) => (
        <li key={item.title} data-reveal="" className={styles.safeguard} style={cssVars({ "--delay": `${(index % 4) * 80}ms` })}>
          <CheckCircle />
          <h3 className="mt-4 mb-0 text-headline font-semibold tracking-snug">{item.title}</h3>
          <p className="mt-1.5 mb-0 text-body text-secondary">{item.body}</p>
        </li>
      ))}
    </ul>
  );
}
