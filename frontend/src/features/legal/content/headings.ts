import type { LegalSlug } from "@/components/shared/legal/legalLinks";

export const LEGAL_TITLES = {
  terms: "Terms of Service",
  privacy: "Privacy Policy",
  baa: "Business Associate Agreement",
  "acceptable-use": "Acceptable Use Policy",
  subprocessors: "Subprocessors",
  security: "Security Overview",
} as const satisfies Record<LegalSlug, string>;

export const TERMS_HEADINGS = {
  about: "About these Terms",
  definitions: "Definitions",
  service: "The Service",
  accounts: "Accounts and eligibility",
  responsibilities: "Your responsibilities",
  "not-advice": "Decision support, not professional advice",
  compliance: "Compliance and program integrity",
  trial: "Free trial",
  fees: "Fees, billing and renewal",
  "customer-data": "Customer Data and PHI",
  "ai-output": "AI features and Output",
  confidentiality: "Confidentiality",
  security: "Security",
  ip: "Intellectual property",
  feedback: "Feedback",
  "third-party": "Third-party services",
  suspension: "Suspension",
  term: "Term and termination",
  "export-deletion": "Data export and deletion",
  warranties: "Warranties and disclaimers",
  liability: "Limitation of liability",
  indemnities: "Indemnities",
  "export-control": "Export control, sanctions and location of use",
  notices: "Notices",
  changes: "Changes to these Terms",
  law: "Governing law and disputes",
  general: "General",
  contact: "Contact",
} as const;

export const PRIVACY_HEADINGS = {
  scope: "Who we are and what this policy covers",
  collect: "Information we collect",
  use: "How we use information",
  bases: "Legal bases",
  cookies: "Cookies and similar technologies",
  sharing: "How we share information",
  retention: "How long we keep information",
  security: "How we protect information",
  location: "Where information is processed",
  children: "Children",
  rights: "Your US state privacy rights",
  exercise: "How to exercise your rights",
  changes: "Changes to this policy",
  contact: "Contact us",
} as const;

export const BAA_HEADINGS = {
  agreement: "Agreement and effective date",
  definitions: "Definitions",
  permitted: "Permitted uses and disclosures",
  "covered-entity": "Obligations of Covered Entity",
  safeguards: "Safeguards",
  reporting: "Reporting, Security Incidents and Breaches",
  subcontractors: "Subcontractors",
  "individual-rights": "Access, amendment and accounting",
  records: "Books and records",
  location: "Where PHI is stored and processed",
  term: "Term and termination",
  return: "Return or destruction of PHI",
  miscellaneous: "Miscellaneous",
} as const;

export const AUP_HEADINGS = {
  scope: "Scope",
  purpose: "Permitted purpose",
  billing: "No billing or coding misuse",
  data: "No misuse of patient or personal data",
  security: "No security or technical misuse",
  messages: "Messages sent through the Service",
  unlawful: "No other unlawful or harmful use",
  enforcement: "Reporting and enforcement",
  changes: "Changes to this policy",
} as const;

export const SUBPROCESSOR_HEADINGS = {
  overview: "Overview",
  "customer-data": "Subprocessors that may process Customer Data",
  "no-phi": "Service providers that do not receive PHI",
  "sign-in": "Sign-in services",
  changes: "Changes to this list",
} as const;

export const SECURITY_HEADINGS = {
  overview: "Overview",
  hosting: "Hosting and encryption",
  access: "Access control",
  audit: "Audit trail",
  messages: "Patient details stay out of messages and logs",
  ai: "AI processing",
  backups: "Backups and recovery",
  application: "Application and network safeguards",
  deletion: "Retention and deletion",
  customer: "Your part",
  report: "Reporting a vulnerability",
} as const;
