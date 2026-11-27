import { bullets, clauses, paragraph, section } from "../../blocks";
import { LEGAL_PERIODS, SERVICE_FACTS } from "../../config";
import { BAA_HEADINGS } from "../headings";

const { incidentNoticeDays, breachNoticeDays } = LEGAL_PERIODS;

export const BAA_DUTIES = [
  section(
    "covered-entity",
    BAA_HEADINGS,
    clauses(
      ["Notices and restrictions.", "Covered Entity will tell Business Associate of any limitation in its notice of privacy practices under 45 CFR 164.520, any change in or revocation of an Individual’s permission, and any restriction it has agreed to under 45 CFR 164.522, to the extent it may affect Business Associate’s use or disclosure of PHI."],
      ["Permissible requests.", "Covered Entity will not ask Business Associate to use or disclose PHI in any manner that would not be permissible under Subpart E of 45 CFR Part 164 if done by Covered Entity, except as this BAA allows."],
      ["Minimum necessary.", "Covered Entity will submit to the Service only the PHI reasonably needed for the Service and will have every consent and authorization the law requires."],
      ["Account safeguards.", "Covered Entity is responsible for its Authorized Users, including assigning roles, using two-step verification and automatic sign-out, and removing access promptly when it is no longer needed."],
    ),
  ),
  section(
    "safeguards",
    BAA_HEADINGS,
    paragraph(
      `Business Associate will use appropriate administrative, physical and technical safeguards, and comply with Subpart C of 45 CFR Part 164 with respect to Electronic Protected Health Information, to prevent use or disclosure of PHI other than as provided by this BAA, including the requirements of 45 CFR 164.308, 164.310, 164.312 and 164.316. It will keep the policies, procedures and documentation required by 45 CFR 164.316 for at least ${SERVICE_FACTS.recordRetentionYears} years from the date of their creation or the date when they were last in effect, whichever is later.`,
    ),
    paragraph("The safeguards built into the Service currently include:"),
    bullets(
      "encryption of PHI at rest with keys managed in AWS Key Management Service, and encryption in transit with TLS over public networks and on every connection to the database and document storage;",
      "separation of each customer’s data and role-based access within each account;",
      "two-step verification and automatic sign-out after a period of inactivity chosen by Covered Entity;",
      `a log of every view, change and export of PHI, including views and exports of the log itself, kept for the period Covered Entity chooses, from ${SERVICE_FACTS.accessLogYears} to ${SERVICE_FACTS.accessLogMaxYears} years;`,
      "records of every model run, suggestion, decision, code-set change, note revision, provider answer and before-and-after change that the database keeps append-only, so that the application cannot change or delete them, and a hash chain over the access log that lets Business Associate detect an altered entry or a gap in the chain;",
      `document links that expire after ${SERVICE_FACTS.documentLinkSeconds} seconds, and no PHI in email or text messages, storage keys, web addresses or application logs;`,
      `monthly database backups kept for ${SERVICE_FACTS.backupYears} years, and document storage that keeps every version of every stored file under a ${SERVICE_FACTS.documentLockYears}-year retention lock.`,
    ),
  ),
  section(
    "reporting",
    BAA_HEADINGS,
    clauses(
      ["Improper use or disclosure.", `Business Associate will report to Covered Entity any use or disclosure of PHI not provided for by this BAA of which it becomes aware, without unreasonable delay and no later than ${incidentNoticeDays} calendar days after becoming aware of it.`],
      ["Security Incidents.", `Business Associate will report any successful Security Incident of which it becomes aware, without unreasonable delay and no later than ${incidentNoticeDays} calendar days after becoming aware of it. This BAA is notice, and no further report is required, of unsuccessful attempts that do not result in unauthorized access, use, disclosure, modification or destruction of PHI or interference with system operations, such as pings, port scans, denial-of-service attempts, blocked sign-in attempts and malware that is stopped.`],
      ["Breaches of Unsecured PHI.", `Business Associate will notify Covered Entity of any Breach of Unsecured Protected Health Information without unreasonable delay and in no case later than ${breachNoticeDays} calendar days after Discovery, as required by 45 CFR 164.410.`],
    ),
    paragraph("Each Breach notice will include, to the extent known and as more becomes available:"),
    bullets(
      "the identity of each Individual whose Unsecured PHI has been, or is reasonably believed to have been, accessed, acquired, used or disclosed;",
      "a description of what happened, including the date of the Breach and the date of Discovery;",
      "the types of Unsecured PHI involved;",
      "steps Individuals should take to protect themselves from potential harm;",
      "what Business Associate is doing to investigate, to mitigate harm and to protect against further Breaches;",
      "a contact person, and any other information Covered Entity reasonably needs to meet its obligations under 45 CFR 164.404 to 164.408.",
    ),
    clauses(
      ["Law enforcement delay.", "If a law enforcement official states that a notice would impede a criminal investigation or damage national security, Business Associate may delay notice as provided in 45 CFR 164.412."],
      ["Mitigation and cooperation.", "Business Associate will mitigate, to the extent practicable, any harmful effect known to it of a use or disclosure of PHI in violation of this BAA, and will cooperate with Covered Entity’s risk assessment and response."],
      ["Notifications.", "Covered Entity is responsible for notifying Individuals, the Secretary and the media where the law requires, unless the parties agree in writing that Business Associate will do so. Where a Breach results from Business Associate’s failure to meet this BAA, Business Associate will reimburse Covered Entity’s reasonable, documented costs of the notifications the law requires, subject to the limitations of liability in the Terms."],
      ["How reports are made.", "Reports go by email to the administrators on Covered Entity’s account and to any security contact Covered Entity gives Business Associate in writing."],
    ),
  ),
];
