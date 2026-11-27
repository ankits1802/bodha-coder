import { clauses, paragraph, section, table } from "../../blocks";
import { LEGAL_PARTY, LEGAL_PERIODS } from "../../config";
import { LEGAL_TITLES, PRIVACY_HEADINGS } from "../headings";

const { company, address, privacyEmail } = LEGAL_PARTY;

export const PRIVACY_RIGHTS = [
  section(
    "rights",
    PRIVACY_HEADINGS,
    paragraph(
      "If you live in California or another US state with a comprehensive privacy law, such as Colorado, Connecticut, Oregon, Texas, Utah or Virginia, you may have the following rights, subject to exceptions and to the extent those laws apply to us:",
    ),
    clauses(
      ["Know and access:", "to know what personal information we collect, use and disclose, and to get a copy of it."],
      ["Delete:", "to ask us to delete personal information we collected from you."],
      ["Correct:", "to ask us to correct inaccurate personal information."],
      ["Portability:", "to receive your personal information in a usable format."],
      ["Opt out:", "of the sale or sharing of personal information, targeted advertising and profiling with significant effects. We do none of these."],
      ["Limit sensitive information:", "we use sensitive personal information, such as account passwords and sign-in credentials, only to provide and secure the Service."],
      ["Non-discrimination:", "we will not treat you differently for exercising your rights."],
      ["Appeal:", "if we decline your request, you can appeal by replying to our decision. If we deny the appeal, you may contact your state attorney general."],
    ),
    table({
      caption: "Personal information we collected in the last 12 months",
      columns: ["Category", "Examples", "Sources", "Disclosed to"],
      rows: [
        ["Identifiers", "Name, email address, account identifier, IP address", "You, your organization, sign-in services, automatically", "Service providers, your organization"],
        ["Professional information", "Organization, role, provider contact details", "You, your organization", "Service providers, your organization"],
        ["Internet activity", "Access log, signed-in devices, service logs", "Automatically", "Service providers, your organization"],
        ["Commercial information", "Subscription and billing records", "You, payment processors", "Service providers, payment processors"],
        ["Sensitive personal information", "Password and sign-in credentials", "You", "Not disclosed"],
      ],
    }),
    paragraph(
      "We have not sold or shared personal information in the last 12 months. Protected health information governed by HIPAA, and medical information governed by California’s Confidentiality of Medical Information Act, are exempt from these state laws and are handled under the BAA.",
    ),
  ),
  section(
    "exercise",
    PRIVACY_HEADINGS,
    paragraph(
      `Email ${privacyEmail} with your request and the email address on your account. We verify requests by confirming that you control that email address and, where needed, by asking for more information. An authorized agent may make a request with your written permission, and we may ask you to confirm your identity directly with us.`,
    ),
    paragraph(
      `We will respond within ${LEGAL_PERIODS.privacyResponseDays} days. Where the law allows, we may extend that once by another ${LEGAL_PERIODS.privacyResponseDays} days and will tell you why.`,
    ),
    paragraph(
      "If your information is in the Service because your organization uses it, we may refer your request to your organization, which controls your account, and help it respond. Requests about patient information go to the health care provider that uploaded it.",
    ),
  ),
  section(
    "changes",
    PRIVACY_HEADINGS,
    paragraph(
      `We may update this ${LEGAL_TITLES.privacy}. We will post each update with a new version number and “Last updated” date, and will notify account administrators by email or in the Service before a material change takes effect.`,
    ),
  ),
  section(
    "contact",
    PRIVACY_HEADINGS,
    table({
      caption: `Contacts for the ${LEGAL_TITLES.privacy}`,
      columns: ["Purpose", "Contact"],
      rows: [
        ["Privacy requests and questions", privacyEmail],
        ["Mail", `${company}, ${address}`],
      ],
    }),
  ),
];
