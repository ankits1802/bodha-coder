import type { ReactNode } from "react";
import styles from "./screen.module.css";

interface ScreenProps {
  title: string;
  aside?: ReactNode;
  children: ReactNode;
}

export function Screen({ title, aside, children }: ScreenProps) {
  return (
    <div className={styles.screen}>
      <div className={styles.bar}>
        <span className={styles.lights}>
          <span />
          <span />
          <span />
        </span>
        <span className={styles.title}>{title}</span>
        <span className={styles.aside}>{aside}</span>
      </div>
      {children}
    </div>
  );
}
