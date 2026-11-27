import type { ReactNode } from "react";
import { cssVars } from "../motion/cssVars";
import styles from "./bento.module.css";

interface TileProps {
  area: string | undefined;
  title: string;
  body: string;
  order: number;
  children: ReactNode;
}

export function Tile({ area, title, body, order, children }: TileProps) {
  return (
    <article data-reveal="" className={`${styles.tile} ${area}`} style={cssVars({ "--delay": `${(order % 3) * 90}ms` })}>
      <div className={styles.text}>
        <h3 className="m-0 font-display text-title2 font-bold tracking-headline">{title}</h3>
        <p className="mt-1.5 mb-0 text-body-lg text-secondary">{body}</p>
      </div>
      <div aria-hidden="true" className={styles.art} data-live="">
        {children}
      </div>
    </article>
  );
}
