import { bullets, paragraph, section } from "../blocks";
import { LEGAL_PARTY, SERVICE_FACTS } from "../config";
import type { LegalDocumentData } from "../types";
import { LEGAL_TITLES, SECURITY_HEADINGS } from "./headings";

const { product, securityEmail, vertexRegion } = LEGAL_PARTY;
const facts = SERVICE_FACTS;

export const SECURITY: LegalDocumentData = {
  slug: "security",
  title: LEGAL_TITLES.security,
  summary: `The safeguards built into ${product}.`,
  version: "1.2",
  updated: "2026-11-28",
  numbered: false,
  sections: [
    section(
      "overview",
      SECURITY_HEADINGS,
      paragraph(
        `${product} is built to handle protected health information. This page describes the safeguards in place today. We sign a ${LEGAL_TITLES.baa} with every customer before patient information is uploaded. We do not claim any third-party certification or attestation.`,
      ),
    ),
    section(
      "hosting",
      SECURITY_HEADINGS,
      bullets(
        `The Service runs on Amazon Web Services in the United States (${facts.region}).`,
        "The database and document storage are encrypted at rest with keys managed in AWS Key Management Service, rotated automatically. Secrets such as database credentials are kept encrypted in AWS Secrets Manager.",
        "Document storage blocks all public access, refuses any request that does not use TLS, and keeps earlier versions of files.",
        "Connections to the Service use HTTPS, and the database accepts only encrypted connections.",
        "Passwords are stored as salted bcrypt hashes. Two-step verification secrets are stored encrypted and recovery codes only as hashes.",
      ),
    ),
    section(
      "access",
      SECURITY_HEADINGS,
      bullets(
        "Each practice’s data is kept separate: every request is checked against the practice of the person making it, and every action against the roles allowed to take it.",
        "Two-step verification with an authenticator app is on by default for administrators and compliance staff, and practices can require it for any role.",
        `People are signed out automatically after ${facts.signOutMinutes} minutes of inactivity, as the practice chooses.`,
        `Access tokens last ${facts.accessTokenMinutes} minutes and are held only in memory. Session tokens are stored hashed, replaced on every use and expire after ${facts.sessionIdleMinutes} minutes without use.`,
        "Blocking a person, changing their role or resetting their password ends their sessions at once. Anyone can review their signed-in devices and sign them out.",
        "Sign-in, password reset, sign-up and one-time code attempts are rate limited.",
        "Sign-in with Google, Microsoft or Yahoo uses OpenID Connect with PKCE, and accepts only verified email addresses.",
      ),
    ),
    section(
      "audit",
      SECURITY_HEADINGS,
      bullets(
        "Every time someone opens, changes or exports a patient record, the access log records who, what, when, the IP address and the device.",
        `The access log is kept for ${facts.accessLogYears} years by default; a practice can choose up to ${facts.accessLogMaxYears}.`,
        "Every model run, suggestion with its reasoning and evidence, decision, code-set change and note revision is kept as its own record and never overwritten.",
        "A decision that departs from Bodha’s suggestion, and every hand edit of the billed codes or diagnosis links, carries the reason the person chose, with who, their role and when.",
        "Approving a claim freezes it as its own record: the codes, the decisions with their reasons, the approver and the model, prompt and document it came from. Claim exports use that record and keep the exact file with its SHA-256.",
        "Provider confirmations, the wording the provider accepted and review comments are kept as written; the database refuses to change these records.",
      ),
    ),
    section(
      "signatures",
      SECURITY_HEADINGS,
      bullets(
        "Each person who approves claims or decides on compliance adopts a signature once: drawn, typed as their full name, or a photo. Providers sign on the secure link and may keep their signature for the next request at the same practice. Replacing a signature keeps the earlier one as a record.",
        "Every approval, compliance decision, provider addendum, visit level statement and agreement accepted at sign-up records the signature, the typed name, the role or credential, the time, the IP address and the device.",
        "Each of these is written as a signed record holding the SHA-256 fingerprint of the document and of the approved content, sealed with a key held in AWS Key Management Service that cannot be exported. The database refuses to change or delete these records.",
        "Every audit defense packet and audit package carries a certificate for each signature, with a verification code anyone can check on the verification page. The page shows the practice, the signer, the time and the fingerprints, and no patient details.",
      ),
    ),
    section(
      "messages",
      SECURITY_HEADINGS,
      bullets(
        "Emails and text messages carry a secure link or a code, never a patient’s name or clinical details.",
        "Provider question links carry their token after the # in the address, so it is not sent to servers or logs, and they require a one-time code sent to the provider’s contact on file. Links expire.",
        `Documents open only through signed links that expire after ${facts.documentLinkSeconds} seconds.`,
        "Stored files are named by identifiers only; file names that may contain patient names are replaced on arrival.",
        "Application logs record identifiers only: no names, email addresses, IP addresses, search text or note content. Database logs exclude query values.",
      ),
    ),
    section(
      "ai",
      SECURITY_HEADINGS,
      bullets(
        `Notes with patient information are read by Google Gemini on Vertex AI, under Google’s business associate terms, in a United States region (${vertexRegion}).`,
        "Google does not use customer data to train its models. We train our own models only on data de-identified under the HIPAA Safe Harbor standard, as the Terms and the BAA describe. The Gemini Developer API is used only with synthetic test data.",
        "The model proposes; people approve. Every suggested code is checked against the official code set for the date of service, and every suggestion quotes its evidence from the note.",
        "Each analysis records the model and prompt version it used.",
        "A drawn or photographed signature is checked by Gemini to confirm it is one handwritten signature before it is kept; the check sees only the signature image.",
      ),
    ),
    section(
      "backups",
      SECURITY_HEADINGS,
      bullets(
        `The database is backed up automatically with point-in-time recovery, kept for ${facts.backupDays} days, and protected against deletion.`,
        `Deleted or replaced documents can be recovered for ${facts.documentVersionDays} days from versioned storage.`,
      ),
    ),
    section(
      "application",
      SECURITY_HEADINGS,
      bullets(
        "Pages load no third-party scripts. A content security policy, frame blocking and strict referrer settings are sent with every page.",
        "Application containers run as non-root users. Dependencies are pinned to exact versions.",
        "Every change is tested automatically before release, and the code is scanned with CodeQL. Infrastructure is defined as code.",
      ),
    ),
    section(
      "deletion",
      SECURITY_HEADINGS,
      paragraph(
        `When a practice leaves, we delete every record and stored file that belongs to it, keeping only a note that it existed and when it was deleted. Earlier file versions expire within ${facts.documentVersionDays} days and backups within ${facts.backupDays} days. The ${LEGAL_TITLES.terms} and the ${LEGAL_TITLES.baa} describe the process.`,
      ),
    ),
    section(
      "customer",
      SECURITY_HEADINGS,
      bullets(
        "Require two-step verification for every role that can see patient information.",
        "Choose a short automatic sign-out time.",
        "Remove people promptly when they leave, and review the access log regularly.",
        "Use test data until a business associate agreement is in place.",
      ),
    ),
    section(
      "report",
      SECURITY_HEADINGS,
      paragraph(
        `Report a suspected vulnerability or incident to ${securityEmail}. Please do not access data that is not yours, disrupt the Service or make the issue public before we have had a reasonable time to fix it. We will not pursue legal action against researchers who act in good faith and follow these rules.`,
      ),
    ),
  ],
};
