import { clauses, paragraph, section } from "../../blocks";
import { LEGAL_PARTY, LEGAL_PERIODS } from "../../config";
import { LEGAL_TITLES, TERMS_HEADINGS } from "../headings";

const { securityEmail } = LEGAL_PARTY;

export const TERMS_DATA = [
  section(
    "customer-data",
    TERMS_HEADINGS,
    clauses(
      ["Ownership.", "As between you and us, you own Customer Data, including the Output generated for you. We claim no ownership of it."],
      ["Our licence to process.", "You grant us a non-exclusive, royalty-free licence, for the Subscription Term and for as long afterwards as we keep Customer Data under these Terms, to host, copy, transmit, process and display Customer Data only as needed to provide, secure and support the Service for you, to prevent abuse and to comply with law. We process Customer Data on your behalf and on your instructions given through the Service, these Terms and the BAA."],
      ["Business Associate Agreement.", "When Customer Data includes PHI, the BAA applies and is incorporated into these Terms. We use and disclose PHI only as the BAA permits. If anything in these Terms conflicts with the BAA as to PHI, the BAA controls."],
      ["No model training.", "We do not use Customer Data, or data de-identified from it, to train or fine-tune foundation models or any other generally available artificial intelligence model, and our AI provider is not permitted to use it for that purpose. We use Customer Data to generate Output for you, to run the accuracy checks and evaluations that your administrators start within your own account, and to investigate problems you report to us."],
      ["De-identified and aggregated data.", "We may create information that has been de-identified in accordance with 45 CFR 164.514(a) and (b), and aggregated statistics about use of the Service that do not identify you, any individual or any patient, and use them to operate, secure and improve the Service and to report on its performance. We create de-identified information from PHI only as the BAA permits, we will not attempt to re-identify it, and we will not sell it."],
      ["Service data.", "We collect information about how the Service is used, such as sign-ins, feature use, error records and performance measurements. It does not include the content of notes. We use it to operate, secure, support and improve the Service."],
    ),
  ),
  section(
    "ai-output",
    TERMS_HEADINGS,
    paragraph(
      "The Service uses Google Gemini large language models to read notes and propose reviews. When PHI is involved, model requests are sent only to Gemini on Google Cloud Vertex AI, a service covered by Google’s HIPAA business associate terms. Test environments that hold only synthetic data may use the Gemini Developer API.",
    ),
    paragraph(
      "Output is produced by probabilistic models and automated rules. It may be incomplete, inaccurate or out of date, even when it quotes evidence from the note. The Service checks suggested codes against official code sets and shows its evidence to make review easier, but those checks do not guarantee that a code is correct for a particular claim. A qualified person must review Output before relying on it.",
    ),
    paragraph(
      "Similar inputs may produce different Output, and Output for you may resemble Output generated for others. We may change the model, model version or instructions the Service uses in order to maintain or improve quality; each analysis records the model and prompt version it used.",
    ),
    paragraph(
      "Accuracy features, such as blind audits and evaluation runs, report agreement on the samples you choose. They describe past results and are not a promise about future performance.",
    ),
  ),
  section(
    "confidentiality",
    TERMS_HEADINGS,
    paragraph(
      "“Confidential Information” means non-public information that one party discloses to the other and that is marked confidential or that a reasonable person would understand to be confidential, including Customer Data, our non-public product and security information, and the pricing in an Order. It does not include information that becomes public through no fault of the receiving party, that the receiving party already knew without restriction, that it develops independently without using the other party’s information, or that it rightfully receives from a third party without a duty of confidence. PHI remains protected under the BAA even if one of these exceptions would otherwise apply.",
    ),
    paragraph(
      "The receiving party will use Confidential Information only to perform under these Terms, protect it with at least reasonable care, and disclose it only to its employees, contractors, advisers and subprocessors who need to know it and are bound by confidentiality obligations at least as protective as these. It may disclose Confidential Information when the law or a court requires, after giving the disclosing party prompt notice where lawful, so that it can seek protection.",
    ),
    paragraph(
      `These obligations continue for ${LEGAL_PERIODS.confidentialityYears} years after these Terms end, and for trade secrets and Customer Data for as long as they remain confidential or are kept by the receiving party.`,
    ),
  ),
  section(
    "security",
    TERMS_HEADINGS,
    paragraph(
      `We maintain administrative, physical and technical safeguards designed to protect Customer Data, as described in the BAA and our ${LEGAL_TITLES.security}. They include encryption at rest and in transit, role-based access, two-step verification, automatic sign-out after inactivity, a log of every view, change and export of patient records, and backups. We may change our safeguards over time but will not materially reduce the overall protection of Customer Data during your Subscription Term.`,
    ),
    paragraph(
      "We will notify you of Security Incidents and Breaches of Unsecured PHI as the BAA requires, and of any other unauthorized access to Customer Data that we confirm, without unreasonable delay.",
    ),
    paragraph(
      `You must not test the security of the Service without our written permission. Report suspected vulnerabilities to ${securityEmail}.`,
    ),
  ),
];
