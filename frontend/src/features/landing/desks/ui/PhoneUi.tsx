import { cssVars } from "../../motion/cssVars";
import { LANDING_TEXT } from "../../strings";
import styles from "./phone.module.css";
import screen from "./screen.module.css";

function Check({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" className={className}>
      <path d="M3.5 8.5l3 3 6-7" pathLength={1} />
    </svg>
  );
}

export function PhoneUi() {
  const words = LANDING_TEXT.deskUi.phone;
  return (
    <div className={styles.phone}>
      <div className={styles.island} />
      <div className={styles.screen}>
        <p className="m-0 text-caption font-semibold text-secondary">{words.title}</p>
        <div className={styles.card}>
          <p className="m-0 text-footnote">
            <span className={screen.ink}>{words.quote}</span>
          </p>
          <p className="mt-2.5 mb-0 text-subhead font-semibold tracking-snug">{words.question}</p>
          <ul className="mt-2.5 mb-0 flex list-none flex-col gap-1.5 p-0">
            {words.options.map((option, index) => (
              <li key={option} className={styles.option} data-chosen={index === 0} style={cssVars({ "--i": index })}>
                <span className={styles.radio} />
                {option}
              </li>
            ))}
          </ul>
        </div>
        <div className={styles.confirm}>
          <span className={styles.box}>
            <Check className={styles.boxCheck} />
          </span>
          {words.confirm}
        </div>
        <span className={styles.sign}>{words.sign}</span>
        <div className={styles.toast}>
          <Check className={styles.toastCheck} />
          {words.signed}
        </div>
      </div>
    </div>
  );
}
