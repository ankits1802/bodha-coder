import { SHARED_TEXT } from "@/components/shared/strings";

export const LEGAL_DRAFT = false;

export const LEGAL_PARTY = {
  product: SHARED_TEXT.brand,
  company: "Bodha LLC",
  entity: "a limited liability company",
  address: "20 Glen Drive, Woodbury, NY 11797, United States",
  legalEmail: "info@chartmateapp.com",
  privacyEmail: "info@chartmateapp.com",
  securityEmail: "info@chartmateapp.com",
  governingLaw: "New York",
  venue: "New York County, New York",
  effectiveDate: "November 27, 2026",
  liabilityCap: "the total amount the Customer paid us for the Service in the 12 months immediately before the event giving rise to the claim",
  refundPolicy: "Fees are non-refundable except as these Terms or the law require.",
  vertexRegion: "us-central1",
  onshoreAccess: "Business Associate’s workforce and Subcontractors do not access PHI from outside the United States.",
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
