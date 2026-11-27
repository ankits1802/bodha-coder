import { bullets, paragraph, section } from "../../blocks";
import { LEGAL_PERIODS, SERVICE_FACTS } from "../../config";
import { LEGAL_TITLES, TERMS_HEADINGS } from "../headings";

const SURVIVING = [
  TERMS_HEADINGS["customer-data"],
  TERMS_HEADINGS.confidentiality,
  TERMS_HEADINGS.ip,
  TERMS_HEADINGS["export-deletion"],
  TERMS_HEADINGS.warranties,
  TERMS_HEADINGS.liability,
  TERMS_HEADINGS.indemnities,
  TERMS_HEADINGS.law,
  TERMS_HEADINGS.general,
];

const SURVIVING_LIST = new Intl.ListFormat("en-US", { style: "long", type: "conjunction" }).format(SURVIVING.map((name) => `“${name}”`));

export const TERMS_ENDING = [
  section(
    "term",
    TERMS_HEADINGS,
    paragraph("These Terms start when you accept them and continue until every Subscription Term has ended."),
    paragraph(
      `Either party may terminate these Terms or an Order by written notice if the other party materially breaches them and does not cure the breach within ${LEGAL_PERIODS.cureDays} days after receiving notice of it. You may also terminate as the BAA allows. We may terminate immediately by notice if you breach “${TERMS_HEADINGS.compliance}” or the ${LEGAL_TITLES["acceptable-use"]} in a way that exposes us or others to legal liability.`,
    ),
    paragraph(
      "If you terminate because of our uncured material breach, we will refund prepaid fees for the rest of the Subscription Term. On any termination, unpaid fees for the period before termination become due.",
    ),
    paragraph(`Provisions that by their nature should survive termination will survive, including ${SURVIVING_LIST}.`),
  ),
  section(
    "export-deletion",
    TERMS_HEADINGS,
    paragraph(
      "During your Subscription Term you can export your data from the Service at any time, including approved claims data as a claims CSV and as 837P-ready claim lines in CSV or JSON, audit defense packets as PDF, signed addenda as text and the access log as CSV.",
    ),
    paragraph(
      "Records are not deleted while you use the Service. A note uploaded by mistake can be voided: it is hidden from work lists and counts, marked with who voided it, when and why, and kept, and an administrator can restore it.",
    ),
    paragraph(
      `When your subscription ends, your Authorized Users can no longer sign in. For ${LEGAL_PERIODS.exportWindowDays} days after the end date you may ask us in writing to provide an export of your Customer Data in the formats the Service supports, or to reopen access briefly so that you can export it yourself.`,
    ),
    paragraph("After that period we close your organization’s account in the Service. Every Authorized User is signed out and access is blocked, and nothing is deleted. We keep every record and stored file that belongs to your organization, including users, providers, notes and every version of their documents and text, analyses with the prompts and model replies they used, decisions, code sets, provider requests and answers, change history and the access log:"),
    bullets(
      `for at least ${SERVICE_FACTS.recordRetentionYears} years (${SERVICE_FACTS.recordRetentionDays} days) from the date each was created; and`,
      `for at least ${SERVICE_FACTS.recordRetentionYears} years after the account is closed.`,
    ),
    paragraph(
      "We keep these records because the law and payer audits require them, so we cannot delete them earlier at your request. When both periods have passed we purge your organization’s records and stored files, keeping only our own activity record, which shows that the account existed and who closed and purged it and when, and an export of the access log.",
    ),
    paragraph(
      `Monthly database backups are kept for ${SERVICE_FACTS.backupYears} years, and every version of a stored file is kept under a ${SERVICE_FACTS.documentLockYears}-year retention lock from when it was stored, so residual copies of purged data remain until those periods end. Until then they stay encrypted, are used only to restore the Service after a failure or as the law requires, and remain protected by these Terms and the BAA. On request, we will confirm in writing the date by which every copy is gone.`,
    ),
    paragraph(
      `The access log is kept for the period your administrator chooses: ${SERVICE_FACTS.accessLogYears} years by default and up to ${SERVICE_FACTS.accessLogMaxYears} years, and never less than ${SERVICE_FACTS.accessLogYears} years. Sign-in credentials, such as recovery codes, sign-in links and sessions, are not kept for these periods. The BAA governs PHI for as long as we keep it.`,
    ),
  ),
];
