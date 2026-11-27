import { SECTION_IDS } from "../anchors";
import { LANDING_TEXT } from "../strings";
import { EvidenceArt } from "./art/EvidenceArt";
import { HccArt } from "./art/HccArt";
import { MipsArt } from "./art/MipsArt";
import { NcciArt } from "./art/NcciArt";
import { PacketArt } from "./art/PacketArt";
import { RemitArt } from "./art/RemitArt";
import { TrustArt } from "./art/TrustArt";
import styles from "./bento.module.css";
import { Tile } from "./Tile";

export function Bento() {
  const words = LANDING_TEXT.bento;
  return (
    <section id={SECTION_IDS.features} aria-labelledby="features-title" className="scroll-mt-16 bg-muted-panel px-6 py-28 sm:py-32">
      <div className="mx-auto max-w-landing">
        <div className="text-center">
          <h2 id="features-title" data-reveal="" className="m-0 font-display text-hero-sm font-bold tracking-display sm:text-display">
            {words.title}
          </h2>
          <p data-reveal="" className="mt-4 mb-0 text-title3 text-secondary">
            {words.lead}
          </p>
        </div>
        <div className={styles.grid}>
          <Tile area={styles.evidence} order={0} {...words.evidence}>
            <EvidenceArt />
          </Tile>
          <Tile area={styles.ncci} order={1} {...words.ncci}>
            <NcciArt />
          </Tile>
          <Tile area={styles.mips} order={2} {...words.mips}>
            <MipsArt />
          </Tile>
          <Tile area={styles.hcc} order={3} {...words.hcc}>
            <HccArt />
          </Tile>
          <Tile area={styles.remit} order={4} {...words.remit}>
            <RemitArt />
          </Tile>
          <Tile area={styles.trust} order={5} {...words.trust}>
            <TrustArt />
          </Tile>
          <Tile area={styles.packet} order={6} {...words.packet}>
            <PacketArt />
          </Tile>
        </div>
      </div>
    </section>
  );
}
