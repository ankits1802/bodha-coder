import { SHARED_TEXT } from "@/components/shared/strings";

export const LEGAL_DRAFT = true;

export const LEGAL_PARTY = {
  product: SHARED_TEXT.brand,
  company: "[Company legal name]",
  entity: "[entity type and state of incorporation, for example a Delaware corporation]",
  address: "[registered address]",
  legalEmail: "[legal@bodhaai.co, to confirm]",
  privacyEmail: "[privacy@bodhaai.co, to confirm]",
  securityEmail: "[security@bodhaai.co, to confirm]",
  governingLaw: "[governing law state]",
  venue: "[county and state of the courts for disputes]",
  effectiveDate: "[effective date: the date these documents are published]",
  liabilityCap: "[liability cap basis, for example the fees paid or payable by the Customer in the 12 months before the event giving rise to the claim]",
  dataLiabilityCap: "[higher cap, if offered, for breaches of the BAA, confidentiality or security obligations, for example two times the cap above]",
  refundPolicy: "[refund policy, for example: fees are non-refundable except as these Terms or the law require]",
  vertexRegion: "[Vertex AI US region, for example us-central1]",
  onshoreAccess: "[Confirm before publishing: Business Associate’s workforce and Subcontractors do not access PHI from outside the United States.]",
} as const;

export const LEGAL_PERIODS = {
  trialDays: 14,
  trialRetentionDays: 30,
  exportWindowDays: 30,
  priceNoticeDays: 30,
  changeNoticeDays: 30,
  subprocessorNoticeDays: 30,
  cureDays: 30,
  paymentNoticeDays: 10,
  invoiceDays: 30,
  disputeDays: 60,
  incidentNoticeDays: 10,
  breachNoticeDays: 10,
  individualRequestDays: 15,
  forwardRequestDays: 10,
  privacyResponseDays: 45,
  confidentialityYears: 5,
  trialLiabilityDollars: 100,
} as const;

export const SERVICE_FACTS = {
  region: "Amazon Web Services US East (N. Virginia), us-east-1",
  accessLogYears: 6,
  accessLogMaxYears: 10,
  backupDays: 35,
  documentVersionDays: 30,
  operationalLogDays: 400,
  documentLinkSeconds: 60,
  accessTokenMinutes: 15,
  refreshDays: 7,
  sessionIdleMinutes: 30,
  signOutMinutes: "5 to 30",
  oidcCookieMinutes: 10,
  signupCookieMinutes: 30,
} as const;
