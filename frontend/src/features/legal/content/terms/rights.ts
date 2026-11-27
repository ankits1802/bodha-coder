import { clauses, paragraph, section } from "../../blocks";
import { LEGAL_TITLES, TERMS_HEADINGS } from "../headings";

export const TERMS_RIGHTS = [
  section(
    "ip",
    TERMS_HEADINGS,
    paragraph(
      "We and our licensors own the Service, including its software, rules, prompts, model configurations, designs and Documentation, all improvements to them, and all intellectual property rights in them. Subject to these Terms and payment of fees, we grant you a non-exclusive, non-transferable, non-sublicensable right during the Subscription Term for your Authorized Users to use the Service for your internal business purposes.",
    ),
    paragraph(
      "If you are a business associate using the Service for covered entities you serve, you may use it for those covered entities, provided you have a business associate agreement with each of them that permits this use. In that case our BAA with you is a subcontractor business associate agreement.",
    ),
    clauses(
      ["Code sets and reference data.", "The Service uses third-party code sets and reference data, including ICD-10-CM from the Centers for Disease Control and Prevention and fee schedule, HCC and quality measure files from the Centers for Medicare & Medicaid Services. They remain the property of their owners and are subject to their terms."],
      ["CPT.", "CPT® is a registered trademark of the American Medical Association (AMA). CPT codes are copyright the AMA, and any CPT content in the Service is subject to the AMA’s terms."],
      ["Restrictions.", `Except as the law permits, you must not copy, modify or create derivative works of the Service; reverse engineer it or try to obtain its source code, prompts or model configurations; resell or sublicense it, or offer it to others as a service, except as these Terms or your Order allow; use it to build a competing product; remove proprietary notices; or use it in breach of the ${LEGAL_TITLES["acceptable-use"]}.`],
    ),
  ),
  section(
    "feedback",
    TERMS_HEADINGS,
    paragraph(
      "If you give us suggestions or feedback about the Service, we may use them without restriction or obligation to you. Feedback does not include Customer Data, and we will not identify you as its source without your permission.",
    ),
  ),
  section(
    "third-party",
    TERMS_HEADINGS,
    paragraph(
      `The Service relies on the subprocessors listed on our ${LEGAL_TITLES.subprocessors} page. It also lets Authorized Users sign in with Google, Microsoft or Yahoo accounts; those services are provided by their owners under their own terms and privacy policies, and we receive only the identity details described in our ${LEGAL_TITLES.privacy}.`,
    ),
    paragraph(
      "Files you export from the Service into other products, such as a billing system or electronic health record, are governed by your agreements with those products’ providers. We are not responsible for third-party products we do not provide.",
    ),
  ),
  section(
    "suspension",
    TERMS_HEADINGS,
    paragraph(
      `We may suspend access to all or part of the Service, for no longer than reasonably needed, if your use poses a security risk to the Service or others; if we reasonably believe the Service is being used in breach of the ${LEGAL_TITLES["acceptable-use"]} or for fraudulent or unlawful purposes, including preparing false claims; if payment is overdue as described in “${TERMS_HEADINGS.fees}”; or if the law requires it. Where practical, we will tell you in advance and give you a chance to fix the problem. Suspension does not delete Customer Data.`,
    ),
  ),
];
