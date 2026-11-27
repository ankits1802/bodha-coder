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
      `When your subscription ends, your Authorized Users can no longer sign in. For ${LEGAL_PERIODS.exportWindowDays} days after the end date you may ask us in writing to provide an export of your Customer Data in the formats the Service supports, or to reopen access briefly so that you can export it yourself.`,
    ),
    paragraph("After that period, or sooner if you ask in writing, we delete your organization’s account in the Service:"),
    bullets(
      "every record that belongs to it, including users, providers, notes and their history, provider requests, analyses and the access log;",
      "every stored document and file, including uploaded PDFs, model replies and remittance files;",
      "keeping only a minimal record that the account existed, who deleted it and when.",
    ),
    paragraph(
      `Earlier versions of stored documents remain in versioned storage for up to ${SERVICE_FACTS.documentVersionDays} days after deletion and then expire. Database backups are kept for up to ${SERVICE_FACTS.backupDays} days and then expire. Until they expire, these residual copies stay encrypted, are used only to restore the Service after a failure, and remain protected by these Terms and the BAA. On request, we will confirm in writing the date by which every copy is gone.`,
    ),
    paragraph(
      `While you are a customer, the access log is kept for the period your administrator chooses: ${SERVICE_FACTS.accessLogYears} years by default and up to ${SERVICE_FACTS.accessLogMaxYears} years. We do not keep an archive for you after deletion, so export anything you must retain before your data is deleted. If the law requires us to keep some Customer Data longer, or returning or destroying PHI is not feasible, the BAA governs that data for as long as we keep it.`,
    ),
  ),
];
