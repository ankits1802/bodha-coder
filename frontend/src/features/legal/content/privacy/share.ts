import { clauses, paragraph, section, table } from "../../blocks";
import { LEGAL_PARTY, SERVICE_FACTS } from "../../config";
import { LEGAL_TITLES, PRIVACY_HEADINGS } from "../headings";

const { vertexRegion } = LEGAL_PARTY;

export const PRIVACY_SHARE = [
  section(
    "sharing",
    PRIVACY_HEADINGS,
    paragraph("We share personal information only as follows:"),
    clauses(
      ["Service providers.", `Companies that host and run the Service for us, under contracts that allow them to use the information only to provide services to us. They are listed on our ${LEGAL_TITLES.subprocessors} page.`],
      ["Your organization.", "Your organization’s administrators and compliance staff can see account users’ details and activity, including the access log."],
      ["Payment processors.", "Stripe and PayPal receive billing contact details and the organization name to take payment, and handle payment details under their own privacy policies."],
      ["Sign-in services.", "When you sign in with Google, Microsoft or Yahoo, that company learns that you used it to sign in to the Service, under its own privacy policy."],
      ["Legal and safety.", "When required by law, subpoena or court order, or when needed to protect the rights, safety and security of our customers, users, patients, the public or us."],
      ["Business transfers.", "To a buyer or successor in a merger, acquisition, financing or sale of assets, who must continue to protect the information as this policy describes and, for PHI, as the BAA requires."],
      ["With your direction.", "When you ask us to, or agree that we may."],
    ),
  ),
  section(
    "retention",
    PRIVACY_HEADINGS,
    table({
      caption: "How long we keep personal information",
      columns: ["Information", "How long"],
      rows: [
        ["Account information", "While your organization’s account exists. Deleted with the account when the organization leaves the Service."],
        ["Access log", `The period your organization chooses: ${SERVICE_FACTS.accessLogYears} years by default and up to ${SERVICE_FACTS.accessLogMaxYears}. Older entries are deleted each day.`],
        ["Signed-in devices", `Until you sign out, the session expires after ${SERVICE_FACTS.refreshDays} days, or ${SERVICE_FACTS.sessionIdleMinutes} minutes pass without use.`],
        ["Service logs", `Up to ${SERVICE_FACTS.operationalLogDays} days.`],
        ["Security signals", "Removed once the longest rate-limit window, one hour, has passed."],
        ["Demo requests and correspondence", "As long as needed to respond and follow up, and no longer than two years after our last contact."],
        ["Billing records", "As long as tax and accounting law requires, usually seven years."],
        ["Agreement records", "For as long as the customer relationship lasts and afterwards for as long as needed to show what was agreed."],
        ["Backups", `Database backups for up to ${SERVICE_FACTS.backupDays} days; earlier versions of stored documents for up to ${SERVICE_FACTS.documentVersionDays} days.`],
      ],
    }),
  ),
  section(
    "security",
    PRIVACY_HEADINGS,
    paragraph(
      `We protect personal information with encryption at rest and in transit, role-based access, two-step verification, automatic sign-out after inactivity, an access log and backups. Our ${LEGAL_TITLES.security} describes these safeguards in more detail. No system is perfectly secure, so please keep your password and two-step verification device safe and tell us about any concern.`,
    ),
  ),
  section(
    "location",
    PRIVACY_HEADINGS,
    paragraph(
      `We host the Service in the United States, in ${SERVICE_FACTS.region}, and process AI requests on Google Cloud in the United States (${vertexRegion}). If you use the Service or visit our website from outside the United States, your information is transferred to and processed in the United States, where data protection law may differ from the law where you live. Payment processors and sign-in services may process information in other countries under their own policies.`,
    ),
  ),
  section(
    "children",
    PRIVACY_HEADINGS,
    paragraph(
      "The Service is for organizations and is not directed to children. We do not knowingly collect personal information from children through our website or accounts. Children’s health information may appear in visit notes uploaded by pediatric practices; that information is PHI handled under the BAA, not under this policy.",
    ),
  ),
];
