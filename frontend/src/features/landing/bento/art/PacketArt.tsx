import { cssVars } from "../../motion/cssVars";
import { LANDING_TEXT } from "../../strings";
import styles from "./packet.module.css";

const WIDTHS = ["82%", "64%", "74%"];

function Marks({ file }: { file: string }) {
  return (
    <>
      <span className={styles.tag}>{file}</span>
      <svg viewBox="0 0 64 64" className={styles.seal}>
        <circle cx="32" cy="32" r="28" />
        <path d="M20 33 l8 8 l16 -18" pathLength={1} />
      </svg>
    </>
  );
}

export function PacketArt() {
  const words = LANDING_TEXT.bentoUi.packet;
  return (
    <div className={styles.desk}>
      <div className={styles.fan}>
        {words.sheets.map((sheet, index) => (
          <div key={sheet} className={styles.sheet} style={cssVars({ "--n": index })}>
            <span className={styles.sheetTitle}>{sheet}</span>
            {WIDTHS.map((width) => (
              <span key={width} className={styles.line} style={cssVars({ "--w": width })} />
            ))}
            {index === words.sheets.length - 1 ? <Marks file={words.file} /> : null}
          </div>
        ))}
      </div>
      <span className={styles.caption}>{words.title}</span>
    </div>
  );
}
