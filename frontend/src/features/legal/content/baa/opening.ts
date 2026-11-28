import { clauses, links, paragraph, section } from "../../blocks";
import { LEGAL_PARTY } from "../../config";
import { BAA_HEADINGS, LEGAL_TITLES } from "../headings";

const { product, company } = LEGAL_PARTY;

export const BAA_OPENING = [
  section(
    "agreement",
    BAA_HEADINGS,
    paragraph(
      `This ${LEGAL_TITLES.baa} (this “BAA”) is between ${company} (“Business Associate”) and the customer that accepts it (“Covered Entity”). It forms part of the ${product} ${LEGAL_TITLES.terms} (the “Terms”). It takes effect on the earliest of the date Covered Entity accepts it while signing up for or using the Service, the date Covered Entity accepts the Terms after this BAA is published, and the date of a signed Order that refers to it (the “BAA Effective Date”).`,
    ),
    paragraph(
      "Business Associate provides the Service, which involves creating, receiving, maintaining or transmitting protected health information on behalf of Covered Entity. This BAA sets out the parties’ obligations under the HIPAA Rules, including 45 CFR 164.502(e) and 164.504(e).",
    ),
    paragraph(
      "If the customer is itself a business associate of one or more covered entities, then “Covered Entity” in this BAA means that customer, Business Associate acts as its subcontractor under 45 CFR 164.502(e)(1)(ii) and 164.504(e)(5), and the customer is responsible for having business associate agreements with its covered entities that permit this arrangement.",
    ),
    paragraph(
      "Enterprise customers may sign a negotiated business associate agreement instead. A signed agreement replaces this BAA for that customer.",
    ),
    links("terms", "subprocessors", "security"),
  ),
  section(
    "definitions",
    BAA_HEADINGS,
    paragraph(
      "Capitalized terms used but not defined in this BAA, or in the Terms, have the meanings given in the HIPAA Rules, including Breach, Data Aggregation, Designated Record Set, Disclosure, Electronic Protected Health Information, Health Care Operations, Individual, Minimum Necessary, Required by Law, Secretary, Security Incident, Subcontractor, Unsecured Protected Health Information and Use.",
    ),
    clauses(
      ["“HIPAA Rules”", "means the Privacy, Security, Breach Notification and Enforcement Rules at 45 CFR Parts 160 and 164, as amended, including by the Health Information Technology for Economic and Clinical Health Act."],
      ["“Protected Health Information” or “PHI”", "has the meaning given in 45 CFR 160.103, limited to information that Business Associate creates, receives, maintains or transmits on behalf of Covered Entity under the Terms. It includes Electronic Protected Health Information."],
      ["“Discovery”", "of a Breach has the meaning given in 45 CFR 164.410(a)(2)."],
      ["“Service”, “Order” and “Subscription Term”", "have the meanings given in the Terms."],
    ),
  ),
  section(
    "permitted",
    BAA_HEADINGS,
    clauses(
      ["Providing the Service.", "Business Associate may use and disclose PHI only to perform the Service for Covered Entity as described in the Terms, including reviewing visit notes against billed codes, generating suggestions and provider questions, sending provider queries, keeping audit records, preparing claims exports and matching remittances, and as Required by Law."],
      ["Retrieving records at Covered Entity’s direction.", "When Covered Entity connects an electronic health record system it uses to the Service, Business Associate may retrieve from that system, with the access Covered Entity grants and only while the connection is on, the signed visit notes of the types Covered Entity chooses and the encounter and practitioner details needed to place them, to perform the Service. Covered Entity is responsible for authorizing that access with its system’s vendor and may pause or end it at any time."],
      ["Management and administration.", "Business Associate may use PHI for its proper management and administration or to carry out its legal responsibilities. It may disclose PHI for those purposes only if the disclosure is Required by Law, or if it obtains reasonable assurances from the recipient that the PHI will be held confidentially, used or further disclosed only as Required by Law or for the purpose for which it was disclosed, and that the recipient will notify Business Associate of any instance it knows of in which the confidentiality of the PHI has been breached."],
      ["Data Aggregation.", "Business Associate will not combine Covered Entity’s PHI with PHI of other covered entities, except to provide Data Aggregation services relating to Covered Entity’s Health Care Operations that Covered Entity requests in writing."],
      ["De-identification.", "Business Associate may de-identify PHI under the Safe Harbor standard in 45 CFR 164.514(b)(2), as 45 CFR 164.502(d) permits, and may use the de-identified information as the Terms permit, including for benchmarking, improving the Service and training machine learning models. Information de-identified under that standard is not PHI."],
      ["Prohibited uses.", "Business Associate will not use or disclose PHI in a manner that would violate Subpart E of 45 CFR Part 164 if done by Covered Entity, except as permitted above for management and administration and Data Aggregation. Business Associate will not sell PHI or use or disclose it for marketing or fundraising."],
      ["Minimum necessary.", "Business Associate will request, use and disclose only the minimum PHI necessary for the intended purpose, in accordance with 45 CFR 164.502(b) and 164.514(d) and any minimum necessary policies Covered Entity gives it in writing."],
    ),
  ),
];
