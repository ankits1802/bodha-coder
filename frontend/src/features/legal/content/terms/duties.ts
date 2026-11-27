import { clauses, paragraph, section } from "../../blocks";
import { LEGAL_PERIODS } from "../../config";
import { LEGAL_TITLES, TERMS_HEADINGS } from "../headings";

export const TERMS_DUTIES = [
  section(
    "responsibilities",
    TERMS_HEADINGS,
    clauses(
      ["Documentation.", "You are responsible for the accuracy and completeness of the clinical documentation and data you submit. The Service reviews what is documented; it cannot detect services that were performed but not recorded, or records that are inaccurate."],
      ["Coding decisions.", "Code selection, claim content and the decision to bill remain your responsibility and the professional responsibility of your providers and certified coders. A qualified person should review every suggestion before it is approved."],
      ["Claims.", "You are solely responsible for every claim you submit to any payer, including Medicare, Medicaid and commercial plans, and for meeting payer rules, coverage requirements and medical necessity standards."],
      ["Provider questions and addenda.", "You are responsible for how provider questions are used and for making sure every addendum reflects the provider’s own clinical judgment."],
      ["Lawful use.", `You must use the Service in compliance with applicable law, including HIPAA, state privacy and medical records laws, the federal False Claims Act, the Anti-Kickback Statute and payer program rules, and with the ${LEGAL_TITLES["acceptable-use"]}.`],
      ["Authority to share.", "You must have every consent, authorization and notice required by law to submit Customer Data to the Service, including PHI."],
      ["Your systems.", "You are responsible for your own devices, networks, email systems and the security of files before they reach the Service."],
    ),
  ),
  section(
    "not-advice",
    TERMS_HEADINGS,
    paragraph(
      "The Service is a decision-support tool. It does not provide legal, billing, coding, reimbursement or medical advice, and it does not practice medicine. Suggestions, references to coding guidelines, code sets and payer rules, Medicare fee estimates and risk scores help qualified people make decisions. They are not a guarantee of payment, coverage or the outcome of any audit.",
    ),
    paragraph(
      "Code sets, guidelines and payer rules change. The Service checks suggested codes against the code-set releases it holds for the date of service, but you remain responsible for confirming that the codes and rules you rely on are current and apply to your claims. Ask your own legal, compliance and coding advisers about questions of law, compliance and payer policy.",
    ),
  ),
  section(
    "compliance",
    TERMS_HEADINGS,
    paragraph(
      "The Service is designed to help you bill the level your documentation supports, whether that is higher or lower than what was billed. You must not use the Service or any Output to upcode, to bill for services that were not rendered or not documented, to unbundle services improperly, to add diagnoses the clinical record does not support, or otherwise to prepare or submit false or fraudulent claims.",
    ),
    paragraph(
      "Submitting claims that you know, or should know, are false can create liability under the federal False Claims Act (31 U.S.C. 3729–3733), the Civil Monetary Penalties Law (42 U.S.C. 1320a-7a) and similar state laws. If you identify an overpayment, you are responsible for reporting and returning it as the law requires, including under 42 U.S.C. 1320a-7k(d).",
    ),
    paragraph(
      "Provider questions created in the Service follow non-leading query practice and contain no payment, reimbursement or risk-score wording. You must not edit or use them to lead a provider toward a particular diagnosis, level or code.",
    ),
    paragraph(
      `The decision history, access log and audit defense packets the Service keeps can support your compliance program, but they do not replace it. We may suspend features or accounts as described in “${TERMS_HEADINGS.suspension}” if we reasonably believe the Service is being used to prepare false claims.`,
    ),
  ),
  section(
    "trial",
    TERMS_HEADINGS,
    paragraph(
      `We may offer a free trial of the Service for ${LEGAL_PERIODS.trialDays} days, or another period we state at sign-up. A trial is for evaluating the Service and includes the features and seats we describe at sign-up.`,
    ),
    paragraph(
      "Do not upload PHI during a trial, or at any other time, unless the BAA is in effect for your organization. The BAA takes effect when you accept it while signing up, or when you and we sign a business associate agreement. Until then, use only test data or data that has been de-identified under HIPAA.",
    ),
    paragraph(
      `When the trial ends, access stops unless you choose a paid plan. A trial’s Customer Data is kept, so that you can continue on a paid plan; if you do not, we close the account and keep its records as described in “${TERMS_HEADINGS["export-deletion"]}”.`,
    ),
    paragraph(
      `During a free trial the Service is provided “as is”, without any warranty, service commitment or indemnity from us, and to the extent the law allows our total liability for the trial is limited to US$${LEGAL_PERIODS.trialLiabilityDollars}. This paragraph does not reduce our obligations to safeguard PHI under the BAA.`,
    ),
  ),
];
