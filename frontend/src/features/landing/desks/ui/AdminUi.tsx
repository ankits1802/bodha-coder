import { LANDING_TEXT } from "../../strings";
import styles from "./admin.module.css";
import { Screen } from "./Screen";
import screen from "./screen.module.css";

function Switch({ on }: { on: boolean }) {
  return <span className={styles.switch} data-on={on} />;
}

function AccessLog() {
  const words = LANDING_TEXT.deskUi.admin;
  const entries = [...words.log, ...words.log];
  return (
    <div className={styles.log}>
      <span className={screen.label}>{words.logTitle}</span>
      <div className={styles.window}>
        <ul className={styles.track}>
          {entries.map((entry, index) => (
            <li key={`${entry.what}-${index}`} className={styles.entry}>
              <span className={styles.dot} />
              <span className="min-w-0 flex-1 truncate">{entry.what}</span>
              <span className="text-secondary">{entry.who}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function AdminUi() {
  const words = LANDING_TEXT.deskUi.admin;
  const [twoStep, ...settings] = words.settings;
  return (
    <Screen title={words.title}>
      {twoStep ? (
        <div className={styles.row}>
          <span className="flex flex-col">
            <span className="font-semibold">{twoStep.label}</span>
            <span className="text-caption text-secondary">{twoStep.value}</span>
          </span>
          <Switch on />
        </div>
      ) : null}
      {settings.map((setting) => (
        <div key={setting.label} className={styles.row}>
          <span className="font-semibold">{setting.label}</span>
          <span className="text-secondary">{setting.value}</span>
        </div>
      ))}
      <div className={styles.row}>
        <span className="font-semibold">{words.autonomy}</span>
        <span className="flex items-center gap-2.5">
          <span className="text-secondary">{words.off}</span>
          <Switch on={false} />
        </span>
      </div>
      <AccessLog />
    </Screen>
  );
}
