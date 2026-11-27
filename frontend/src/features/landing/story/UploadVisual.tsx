import { cssVars } from "../motion/cssVars";
import { LANDING_TEXT } from "../strings";
import styles from "./story.module.css";

const PAGES = [
  { n: 0, r: "-18deg", x: "-60%" },
  { n: 1, r: "12deg", x: "40%" },
  { n: 2, r: "-8deg", x: "-20%" },
  { n: 3, r: "16deg", x: "70%" },
] as const;

const LINES = ["72%", "88%", "64%", "80%", "52%"];

export function UploadVisual() {
  return (
    <div data-index={0} className={styles.visual}>
      <div className={styles.tray}>
        {PAGES.map((page) => (
          <div key={page.n} className={styles.page} style={cssVars({ "--n": page.n, "--r": page.r, "--x": page.x })}>
            <span className={styles.fileTag}>{LANDING_TEXT.story.upload.file}</span>
            {LINES.map((width, index) => (
              <span key={index} className={styles.line} style={cssVars({ "--w": width })} />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
