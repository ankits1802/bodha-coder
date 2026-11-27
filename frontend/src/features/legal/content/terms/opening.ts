import { clauses, links, paragraph, section } from "../../blocks";
import { LEGAL_PARTY } from "../../config";
import { LEGAL_TITLES, TERMS_HEADINGS } from "../headings";

const { product, company, entity, securityEmail } = LEGAL_PARTY;

export const TERMS_OPENING = [
  section(
    "about",
    TERMS_HEADINGS,
    paragraph(
      `These ${LEGAL_TITLES.terms} (the “Terms”) are a binding agreement between ${company}, ${entity} (“we”, “us” or “our”), and the organization that signs up for or uses ${product} (the “Customer” or “you”). They govern your access to and use of ${product}, including its web application, related services and Documentation (together, the “Service”).`,
    ),
    paragraph(
      "By clicking to accept these Terms, signing an order form that refers to them, or using the Service, you agree to them on behalf of the organization you represent and confirm that you have authority to bind it. If you do not have that authority, or do not agree, do not accept these Terms or use the Service.",
    ),
    paragraph(
      `The ${LEGAL_TITLES.baa} (the “BAA”), the ${LEGAL_TITLES["acceptable-use"]} and any order form or plan you select online (an “Order”) form part of these Terms. If they conflict, this order of precedence applies: the BAA, as to Protected Health Information; then a signed Order, as to its specific commercial terms; then these Terms; then the other documents they refer to. The ${LEGAL_TITLES.privacy} explains how we handle personal information about website visitors and account users; it is not part of these Terms.`,
    ),
    paragraph(
      "Enterprise customers may sign a separate written agreement with us. Where they do, that agreement governs to the extent it conflicts with these Terms.",
    ),
    links("baa", "acceptable-use", "privacy", "subprocessors", "security"),
  ),
  section(
    "definitions",
    TERMS_HEADINGS,
    clauses(
      ["“Authorized User”", "means an individual you allow to use the Service under your account, such as your employees, contractors, coders, providers and compliance staff, and providers who answer documentation questions through a secure link."],
      ["“Active Provider”", "means a physician or other qualified health care professional marked as active in your account at any time during a billing period, unless your Order or our pricing page defines it differently."],
      ["“Customer Data”", "means data, documents and information that you or your Authorized Users submit to the Service, including visit notes, billed codes, remittance files, provider answers and settings, and the Output generated from them for you."],
      ["“HIPAA”", "means the Health Insurance Portability and Accountability Act of 1996, the Health Information Technology for Economic and Clinical Health Act, and their implementing regulations at 45 CFR Parts 160 and 164, as amended."],
      ["“Protected Health Information” or “PHI”", "has the meaning given in 45 CFR 160.103, limited to information we create, receive, maintain or transmit on your behalf through the Service."],
      ["“Output”", "means suggestions, codes, findings, evidence quotations, scores, provider questions, summaries, reports and exports that the Service generates from Customer Data."],
      ["“Subscription Term”", "means your trial period or the paid period stated in your Order, including renewals."],
      ["“Documentation”", "means our user guides, help pages and the Security Overview and Subprocessors pages we publish for the Service."],
    ),
  ),
  section(
    "service",
    TERMS_HEADINGS,
    paragraph(
      "The Service reviews clinical visit notes that you upload against the codes you bill, including evaluation and management (E/M) levels, ICD-10-CM diagnoses, modifiers, hierarchical condition categories (HCC), quality measures (MIPS) and clinical documentation integrity (CDI) queries. It suggests corrections with supporting evidence quoted from the note, helps you send non-leading questions to providers, keeps an audit record, exports claims data for your billing system and matches remittance files to your claims.",
    ),
    paragraph(
      "The Service does not submit claims to payers. People in your organization decide which codes to approve and what to bill. Features that approve claims automatically, where offered, are off by default, can be switched on only by your administrators under the conditions shown in the Service, and remain your decision and responsibility when used.",
    ),
    paragraph(
      "We may improve, change or retire features from time to time. We will not materially reduce the core functionality of the Service during a paid Subscription Term without telling you in advance. If we do, you may terminate the affected subscription and we will refund prepaid fees for the remaining period.",
    ),
  ),
  section(
    "accounts",
    TERMS_HEADINGS,
    paragraph(
      "The Service is for organizations, not consumers. It is intended for physician practices and other health care providers in the United States that are covered entities under HIPAA, and for their business associates, such as billing and coding companies. You must be able to form a binding contract under applicable law.",
    ),
    clauses(
      ["Accurate information.", "You must give accurate registration and billing information and keep it current."],
      ["Authorized Users.", "You decide who becomes an Authorized User and which role each one has. You must remove access promptly when someone leaves your organization or no longer needs it."],
      ["One person, one account.", "Each Authorized User must use their own account. Credentials, two-step verification devices and recovery codes must not be shared."],
      ["Two-step verification.", "Two-step verification is on by default for administrators and compliance staff, and your administrators can require it for any other role. We strongly recommend keeping it on for every role that can view PHI; if you turn it off for a role, you accept the added risk."],
      ["Account activity.", `You are responsible for activity under your account. Tell us promptly at ${securityEmail} if you suspect unauthorized access.`],
      ["Seats.", "A trial includes the seats we state at sign-up. Paid plans include the Active Providers and users stated in your Order or on our pricing page."],
    ),
  ),
];
