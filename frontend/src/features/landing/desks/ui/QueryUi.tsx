import { StatusDot } from "@/components/ui/StatusDot";
import { cssVars } from "../../motion/cssVars";
import { LANDING_TEXT } from "../../strings";
import styles from "./query.module.css";
import { Screen } from "./Screen";
import screen from "./screen.module.css";

export function QueryUi() {
  const words = LANDING_TEXT.deskUi.query;
  return (
    <Screen title={words.title}>
      <div className="px-4.5 pt-4.5 pb-4">
        <p className="m-0 text-footnote">
          <span className={screen.ink}>{words.quote}</span>
        </p>
        <p className="mt-3 mb-0 text-body font-semibold tracking-snug">{words.question}</p>
        <ul className="mt-3 mb-0 flex list-none flex-col gap-1.5 p-0">
          {words.options.map((option, index) => (
            <li key={option} className={styles.option} style={cssVars({ "--i": index })} data-chosen={index === 0}>
              <span className={styles.radio} />
              {option}
            </li>
          ))}
        </ul>
      </div>
      <div className={styles.foot}>
        <span className={styles.ticker}>
          <span className={styles.tickerTrack}>
            <StatusDot tone="warn">{words.waiting}</StatusDot>
            <StatusDot tone="ok">{words.answered}</StatusDot>
          </span>
        </span>
      </div>
    </Screen>
  );
}
