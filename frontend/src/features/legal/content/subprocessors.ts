import { paragraph, section, table } from "../blocks";
import { LEGAL_PARTY, LEGAL_PERIODS, SERVICE_FACTS } from "../config";
import type { LegalDocumentData } from "../types";
import { LEGAL_TITLES, SUBPROCESSOR_HEADINGS } from "./headings";

const { product, privacyEmail, vertexRegion } = LEGAL_PARTY;
const COLUMNS = ["Name", "Purpose", "Data processed", "Location"];

export const SUBPROCESSORS: LegalDocumentData = {
  slug: "subprocessors",
  title: LEGAL_TITLES.subprocessors,
  summary: `The companies that process customer data to provide ${product}.`,
  version: "1.2",
  updated: "2026-11-28",
  numbered: false,
  sections: [
    section(
      "overview",
      SUBPROCESSOR_HEADINGS,
      paragraph(
        `These are the third parties that process customer data on our behalf to provide ${product}. Each one that may process protected health information does so under a business associate agreement with us, as the ${LEGAL_TITLES.baa} requires.`,
      ),
    ),
    section(
      "customer-data",
      SUBPROCESSOR_HEADINGS,
      table({
        caption: "Subprocessors that may process Customer Data, including PHI",
        columns: COLUMNS,
        rows: [
          ["Amazon Web Services, Inc.", "Hosting and operations: application containers (ECS on Fargate), database (RDS for PostgreSQL), document storage (S3, encrypted with KMS), encryption keys (KMS), secrets (Secrets Manager), backups (AWS Backup), monitoring and logs (CloudWatch), account activity logging (CloudTrail), and visit notes that practices email to Bodha (SES email receiving and Lambda)", "All Customer Data, including visit notes and other PHI, account data, and service logs that exclude PHI", `United States (${SERVICE_FACTS.region})`],
          ["Amazon Web Services, Inc.", "Email (SES) and text messages (SNS)", "Recipient email addresses and phone numbers, and messages with sign-in links, codes and secure links but no patient details", `United States (${SERVICE_FACTS.region})`],
          ["Google LLC (Google Cloud)", "Gemini models on Vertex AI that read visit notes and propose reviews", "Note text and PDFs, billed codes and the related PHI sent for each review, and signature images to check before they are kept", `United States (${vertexRegion})`],
        ],
      }),
    ),
    section(
      "no-phi",
      SUBPROCESSOR_HEADINGS,
      table({
        caption: "Service providers that do not receive PHI",
        columns: COLUMNS,
        rows: [
          ["Stripe, Inc.", "Payment processing", "Billing contact details, organization name and payment details", "United States; may also process in other countries under its own terms"],
          ["PayPal, Inc.", "Payment processing", "Billing contact details, organization name and payment details", "United States; may also process in other countries under its own terms"],
          ["Google LLC (Gemini Developer API)", "AI model access for testing", "Synthetic test notes only", "Google’s global infrastructure"],
          ["GitHub, Inc.", "Source code hosting and automated testing", "Source code and synthetic test data; no Customer Data", "United States"],
        ],
      }),
    ),
    section(
      "sign-in",
      SUBPROCESSOR_HEADINGS,
      paragraph(
        "Authorized Users may choose to sign in with an existing Google, Microsoft or Yahoo account. These companies act under their own terms when you use them and do not process Customer Data for us.",
      ),
      table({
        caption: "Sign-in services",
        columns: ["Name", "Purpose", "Data exchanged"],
        rows: [
          ["Google LLC", "Optional sign-in with a Google account", "Name, email address, whether it is verified, and an account identifier"],
          ["Microsoft Corporation", "Optional sign-in with a Microsoft work, school or personal account", "Name, email address, whether it is verified, and an account identifier"],
          ["Yahoo Inc.", "Optional sign-in with a Yahoo account", "Name, email address, whether it is verified, and an account identifier"],
        ],
      }),
    ),
    section(
      "changes",
      SUBPROCESSOR_HEADINGS,
      paragraph(
        `We will update this page, and notify customer administrators by email, at least ${LEGAL_PERIODS.subprocessorNoticeDays} days before a new subprocessor begins processing Customer Data. If you object on reasonable data protection grounds within that period, tell us at ${privacyEmail}. We will work with you in good faith, and if we cannot resolve the objection, you may terminate the affected subscription and receive a refund of prepaid fees for the rest of its term. If we must replace a subprocessor urgently to keep the Service running or secure, we will give notice as soon as practicable.`,
      ),
    ),
  ],
};
