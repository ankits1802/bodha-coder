import { clauses, paragraph, section } from "../../blocks";
import { LEGAL_PARTY, LEGAL_PERIODS, SERVICE_FACTS } from "../../config";
import { BAA_HEADINGS, LEGAL_TITLES } from "../headings";

const { vertexRegion, onshoreAccess } = LEGAL_PARTY;
const { individualRequestDays, forwardRequestDays } = LEGAL_PERIODS;

export const BAA_SUPPORT = [
  section(
    "subcontractors",
    BAA_HEADINGS,
    paragraph(
      "In accordance with 45 CFR 164.502(e)(1)(ii) and 164.308(b)(2), Business Associate will ensure that every Subcontractor that creates, receives, maintains or transmits PHI on its behalf agrees in writing to the same restrictions, conditions and requirements that apply to Business Associate under this BAA, including implementing reasonable and appropriate safeguards for Electronic Protected Health Information. Business Associate remains responsible for its Subcontractors’ performance of these obligations.",
    ),
    paragraph(
      `Subcontractors that may process PHI are listed on the ${LEGAL_TITLES.subprocessors} page, including Amazon Web Services for hosting, storage, email and text messages, and Google Cloud for Gemini on Vertex AI, each under its business associate addendum. Business Associate will give notice of new Subcontractors that process PHI as that page describes.`,
    ),
  ),
  section(
    "individual-rights",
    BAA_HEADINGS,
    clauses(
      ["Access.", `To the extent Business Associate maintains PHI in a Designated Record Set, it will make that PHI available to Covered Entity within ${individualRequestDays} days of Covered Entity’s request, in the electronic form and format requested where readily producible, so that Covered Entity can meet 45 CFR 164.524. Covered Entity can usually retrieve this PHI itself through the Service.`],
      ["Amendment.", `Within ${individualRequestDays} days of Covered Entity’s request, Business Associate will make any amendment to PHI in a Designated Record Set that Covered Entity directs under 45 CFR 164.526. The Service records note text and code changes as new revisions, so earlier versions remain part of the record.`],
      ["Accounting of disclosures.", `Business Associate will document disclosures of PHI, and information related to them, as Covered Entity would need to respond to a request for an accounting under 45 CFR 164.528, and will provide that information within ${individualRequestDays} days of Covered Entity’s request. The Service’s access log, which records each view, change and export, is available to Covered Entity directly.`],
      ["Requests made to Business Associate.", `If an Individual asks Business Associate directly for access, amendment or an accounting, Business Associate will forward the request to Covered Entity within ${forwardRequestDays} days and will respond only as Covered Entity directs.`],
      ["Covered Entity’s obligations.", "To the extent Business Associate carries out an obligation of Covered Entity under Subpart E of 45 CFR Part 164, it will comply with the requirements of Subpart E that apply to Covered Entity in performing that obligation."],
    ),
  ),
  section(
    "records",
    BAA_HEADINGS,
    paragraph(
      "Business Associate will make its internal practices, books and records relating to the use and disclosure of PHI available to the Secretary for the purpose of determining compliance with the HIPAA Rules, subject to attorney-client and other applicable legal privileges. Unless the law prohibits it, Business Associate will tell Covered Entity of any such request.",
    ),
  ),
  section(
    "location",
    BAA_HEADINGS,
    paragraph(
      `Business Associate stores and processes PHI in the United States: in ${SERVICE_FACTS.region}, and in Google Cloud Vertex AI in a United States region (${vertexRegion}).`,
    ),
    paragraph(onshoreAccess),
    paragraph(
      "Covered Entity’s own Authorized Users may reach the Service from any location. Covered Entity is responsible for making sure that their access is permitted by law and by its own agreements.",
    ),
  ),
];
