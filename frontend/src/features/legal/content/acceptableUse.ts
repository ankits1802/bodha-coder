import { bullets, paragraph, section } from "../blocks";
import { LEGAL_PARTY } from "../config";
import type { LegalDocumentData } from "../types";
import { AUP_HEADINGS, LEGAL_TITLES, TERMS_HEADINGS } from "./headings";

const { product, securityEmail, legalEmail } = LEGAL_PARTY;

export const ACCEPTABLE_USE: LegalDocumentData = {
  slug: "acceptable-use",
  title: LEGAL_TITLES["acceptable-use"],
  summary: `The rules for using ${product} safely, lawfully and honestly.`,
  version: "0.1",
  updated: "2026-11-27",
  numbered: true,
  sections: [
    section(
      "scope",
      AUP_HEADINGS,
      paragraph(
        `This ${LEGAL_TITLES["acceptable-use"]} applies to every customer and Authorized User of ${product} (the “Service”) and forms part of the ${LEGAL_TITLES.terms}. Words defined in the Terms have the same meaning here. Customers are responsible for their Authorized Users’ compliance.`,
      ),
    ),
    section(
      "purpose",
      AUP_HEADINGS,
      paragraph(
        "Use the Service only for the coding review, clinical documentation improvement, billing preparation, remittance and compliance activities of your organization, or of the covered entities you serve as their business associate, and only in compliance with the law.",
      ),
    ),
    section(
      "billing",
      AUP_HEADINGS,
      paragraph("You must not use the Service or its Output to:"),
      bullets(
        "select or bill a code, level or modifier that the documentation does not support, including upcoding or improper unbundling;",
        "bill for services that were not provided or not documented;",
        "add, alter or back-date documentation to support a code, other than through a dated, signed addendum that reflects the provider’s own clinical judgment;",
        "change provider questions so that they lead toward a particular answer, or mention payment, reimbursement or risk scores;",
        "release claims held for a provider’s answer, or for compliance review, by working around the Service’s controls;",
        "present Output as the opinion of a certified coder, auditor or attorney when it has not been reviewed by one.",
      ),
    ),
    section(
      "data",
      AUP_HEADINGS,
      paragraph("You must not:"),
      bullets(
        "upload PHI before a business associate agreement with us is in effect for your organization;",
        "upload information you are not authorized to share, or more PHI than the Service needs, such as complete medical records when a visit note is enough;",
        "put patient details where they do not belong, such as in practice or folder names, email subjects, support messages, demo requests or feedback;",
        "use the Service to collect or profile information about individuals for purposes other than treatment, payment or health care operations;",
        "attempt to re-identify de-identified information, or to access another customer’s data.",
      ),
    ),
    section(
      "security",
      AUP_HEADINGS,
      paragraph("You must not:"),
      bullets(
        "share accounts, passwords, two-step verification devices or recovery codes;",
        "bypass or weaken two-step verification, roles, automatic sign-out, rate limits or other security controls;",
        "probe, scan or test the Service for vulnerabilities without our written permission;",
        "upload malware, or content designed to manipulate the AI models, such as hidden instructions in documents meant to change Output or reveal system instructions;",
        "overload or disrupt the Service, or access it by automated means other than the exports and interfaces we provide;",
        "copy, reverse engineer or extract the Service’s software, prompts or model configurations.",
      ),
    ),
    section(
      "messages",
      AUP_HEADINGS,
      paragraph(
        "Provider questions are sent by email or text message. Send them only to providers who work with your organization and who have agreed to receive them at the address or number you enter. Text messages carry only secure links, reminders and one-time codes for documentation questions, and recipients may reply STOP to stop receiving them. Do not use the Service to send marketing or unrelated messages.",
      ),
    ),
    section(
      "unlawful",
      AUP_HEADINGS,
      paragraph("You must not use the Service to:"),
      bullets(
        "violate any law or regulation, or the rights of others, including privacy and intellectual property rights;",
        "harass, threaten or defame anyone;",
        "breach United States export control or sanctions laws;",
        "build or train a competing product.",
      ),
    ),
    section(
      "enforcement",
      AUP_HEADINGS,
      paragraph(
        `Report suspected violations or vulnerabilities to ${securityEmail}, and other concerns to ${legalEmail}. We may investigate suspected violations, and may suspend or terminate access as described in “${TERMS_HEADINGS.suspension}” and “${TERMS_HEADINGS.term}” in the Terms. Where the law requires, we may report unlawful activity to the authorities, subject to our obligations under the BAA.`,
      ),
    ),
    section(
      "changes",
      AUP_HEADINGS,
      paragraph(
        `We may update this policy. We will post each update with a new version number and “Last updated” date, and material changes follow “${TERMS_HEADINGS.changes}” in the Terms.`,
      ),
    ),
  ],
};
