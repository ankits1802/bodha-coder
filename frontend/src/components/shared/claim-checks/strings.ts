import type { PayerFlagRule } from "@/lib/api/types";

export const CLAIM_CHECK_TEXT = {
  heading: "Claim checks",
  loading: "Checking the claim",
  retry: "Try again",
  clean: "No claim edits",
  notLoaded: (quarter: string) => `NCCI ${quarter} not loaded for this date`,
  payerNotSet: "Payer not set",
  pair: (first: string, second: string) => `${first} with ${second}`,
  together: "Cannot be billed together",
  modifierAllowed: "Modifier allowed",
  bypassed: (modifier: string) => `Bypassed with ${modifier}`,
  overLimit: (limit: number) => `Units over limit (MUE ${limit})`,
  units: (code: string, units: number) => `${code} ×${units}`,
  noPrimary: "Add-on without its primary",
  earlierInitial: (day: string) => `Earlier initial visit ${day}`,
  rules: {
    telehealth_place: "Telehealth: use POS 02 or 10",
    audio_only_place: "Audio-only needs POS 10",
    home_telehealth_ended: "Home telehealth ended Dec 31, 2027",
    complexity_with_25: "Complexity add-on not paid with 25",
    g2211_replaced: "G2211 replaced by modifier B1",
    level_downcode_risk: "Likely downcode, document MDM",
    audio_only_risk_adjustment: "Audio-only: no risk adjustment",
    nursing_incident_to: "No incident-to in a nursing facility",
    initial_visit_repeated: "Initial visit already billed this stay",
  } satisfies Record<PayerFlagRule, string>,
};
