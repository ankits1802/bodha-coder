import { clauses, paragraph, section } from "../../blocks";
import { LEGAL_PARTY, LEGAL_PERIODS, SERVICE_FACTS } from "../../config";
import { BAA_HEADINGS, TERMS_HEADINGS } from "../headings";

const { privacyEmail, securityEmail } = LEGAL_PARTY;
const { recordRetentionYears: retentionYears, recordRetentionDays: retentionDays } = SERVICE_FACTS;

export const BAA_CLOSING = [
  section(
    "term",
    BAA_HEADINGS,
    paragraph("This BAA starts on the BAA Effective Date and continues until all PHI has been returned or destroyed as this BAA provides."),
    paragraph(
      `If Covered Entity determines that Business Associate has violated a material term of this BAA, Covered Entity may terminate the Terms and this BAA by written notice if Business Associate does not cure the violation within ${LEGAL_PERIODS.cureDays} days after receiving notice of it, or immediately if cure is not possible.`,
    ),
    paragraph(
      `If Business Associate knows of a pattern of activity or practice of Covered Entity that is a material breach of Covered Entity’s obligations under this BAA, Business Associate may terminate the Terms and this BAA on the same basis. This BAA ends when the Terms end, subject to “${BAA_HEADINGS.return}”.`,
    ),
  ),
  section(
    "return",
    BAA_HEADINGS,
    paragraph(
      "When the Terms end, Business Associate will return PHI to Covered Entity and will destroy the PHI that it or its Subcontractors maintain in any form when the retention period ends, as set out below.",
    ),
    clauses(
      ["Return.", `During the Subscription Term, and for ${LEGAL_PERIODS.exportWindowDays} days after it ends, Covered Entity may export its PHI from the Service or ask Business Associate in writing to provide an export in the formats the Service supports.`],
      ["Retention.", `The law requires the records of the Service to be kept after the Terms end, including the documentation requirements of the HIPAA Rules and the record-retention and audit requirements of Medicare, Medicaid and other payers. Business Associate therefore closes Covered Entity’s account in the Service: every Authorized User is signed out and access is blocked, and every database record and stored file belonging to Covered Entity, including notes and every version of their documents and text, analyses, decisions, code sets, provider requests and answers, change history, users and the access log, is kept for at least ${retentionYears} years (${retentionDays} days) from its creation and at least ${retentionYears} years after the account is closed (the “retention period”).`],
      ["Infeasibility.", "The parties agree that returning or destroying the PHI kept for the retention period is infeasible until that period ends. Business Associate will extend the protections of this BAA to that PHI and limit further uses and disclosures to the purposes that make return or destruction infeasible, namely keeping the records, responding to audits and reviews of Covered Entity’s claims, and as Required by Law, for as long as it keeps the PHI. The same applies to any other PHI the law requires Business Associate to keep, and Business Associate will tell Covered Entity why."],
      ["Destruction.", "After the retention period ends, Business Associate will purge Covered Entity’s records and stored files. It keeps only its own activity record, which shows that the account existed and who closed and purged it and when, and an export of the access log, which remain protected by this BAA for as long as they are kept."],
      ["Residual copies.", `Monthly database backups taken before the purge are kept until ${SERVICE_FACTS.backupYears} years after each was taken, and each version of a stored file stays in versioned storage until its ${SERVICE_FACTS.documentLockYears}-year retention lock ends, after which it expires. Until then, residual copies stay encrypted, are used only to restore the Service after a failure or as Required by Law, and remain protected by this BAA.`],
      ["Confirmation.", "On request, Business Associate will confirm in writing the date on which the account was closed, the date on which its records were purged, and the date by which all copies were destroyed."],
    ),
  ),
  section(
    "miscellaneous",
    BAA_HEADINGS,
    clauses(
      ["Regulatory references.", "A reference to a section of the HIPAA Rules means that section as in effect or as amended."],
      ["Amendment.", `The parties will amend this BAA as needed to comply with changes in the HIPAA Rules. Business Associate may update this BAA to reflect changes in law by posting an updated version and notifying Covered Entity; other changes follow “${TERMS_HEADINGS.changes}” in the Terms.`],
      ["Interpretation.", "Any ambiguity in this BAA will be resolved to permit compliance with the HIPAA Rules. If this BAA conflicts with the Terms as to PHI, this BAA controls."],
      ["Liability.", `The exclusions and limitations of liability in “${TERMS_HEADINGS.liability}” in the Terms apply to this BAA unless the parties agree otherwise in a signed agreement.`],
      ["Independent contractor.", "Business Associate acts as an independent contractor and not as an agent of Covered Entity."],
      ["No third-party beneficiaries.", "Nothing in this BAA gives any right or remedy to anyone other than the parties."],
      ["Survival.", `Business Associate’s obligations under “${BAA_HEADINGS.return}”, and its obligations to protect any PHI it keeps, survive the end of this BAA.`],
      ["Governing law and notices.", `This BAA is governed by the law that governs the Terms, except to the extent HIPAA applies. Notices follow the Terms; notices to Business Associate about PHI also go to ${privacyEmail} and ${securityEmail}.`],
    ),
  ),
];
