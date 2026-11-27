import { clauses, paragraph, section, table } from "../../blocks";
import { LEGAL_PARTY, LEGAL_PERIODS } from "../../config";
import { LEGAL_TITLES, TERMS_HEADINGS } from "../headings";

const { company, address, legalEmail, privacyEmail, securityEmail, governingLaw, venue } = LEGAL_PARTY;

export const TERMS_GENERAL = [
  section(
    "export-control",
    TERMS_HEADINGS,
    paragraph(
      "You must comply with United States export control and economic sanctions laws. You must not use the Service, or allow it to be used, in or on behalf of anyone in a country or region subject to comprehensive United States sanctions, or by any person on a United States government restricted party list.",
    ),
    paragraph(
      "The Service is offered for use in the United States. If you allow Authorized Users outside the United States to access PHI through the Service, you are responsible for making sure that this is permitted by law, by your payer contracts and by your own business associate agreements.",
    ),
  ),
  section(
    "notices",
    TERMS_HEADINGS,
    paragraph(
      `We may give you notices by email to the administrators on your account or in the Service. Send legal notices to us by email to ${legalEmail}, with a copy by mail or courier to ${company}, ${address}. A notice takes effect when received; an email notice is treated as received one business day after it is sent unless the sender receives an error message. Notices of breach, termination or an indemnified claim must say so clearly.`,
    ),
  ),
  section(
    "changes",
    TERMS_HEADINGS,
    paragraph(
      `We may update these Terms from time to time. We will post each update with a new version number and “Last updated” date. For material changes we will notify your administrators by email or in the Service at least ${LEGAL_PERIODS.changeNoticeDays} days before they take effect, unless a change is required sooner by law or to address a security risk.`,
    ),
    paragraph(
      "A material change does not apply to a paid Subscription Term already under way unless you agree; it applies from your next renewal. If you do not accept a change, you may cancel before it applies to you. We record which version of these Terms and the BAA your organization accepted, and when.",
    ),
  ),
  section(
    "law",
    TERMS_HEADINGS,
    paragraph(
      `These Terms are governed by the laws of the State of ${governingLaw} and applicable United States federal law, without regard to conflict of laws rules. The United Nations Convention on Contracts for the International Sale of Goods does not apply.`,
    ),
    paragraph(
      `Before starting a formal proceeding, the parties will try for ${LEGAL_PERIODS.cureDays} days to resolve a dispute through good-faith discussions between senior representatives. The state and federal courts located in ${venue} have exclusive jurisdiction over any dispute arising out of or relating to these Terms, and each party consents to their jurisdiction. Each party waives its right to a jury trial in any proceeding arising out of or relating to these Terms. Either party may seek urgent injunctive relief in any court of competent jurisdiction to protect its intellectual property, Confidential Information or PHI.`,
    ),
  ),
  section(
    "general",
    TERMS_HEADINGS,
    clauses(
      ["Entire agreement.", "These Terms, the BAA, the documents they incorporate and any Order are the entire agreement between the parties about the Service and replace any earlier agreement on that subject. Terms in a purchase order or other business form you send do not apply."],
      ["Assignment.", "Neither party may assign these Terms without the other’s written consent, except to a successor in a merger, acquisition or sale of all or substantially all of its relevant business or assets, on notice and provided the successor assumes these Terms and the BAA. Any other assignment is void."],
      ["Force majeure.", "Neither party is liable for delay or failure caused by events beyond its reasonable control, such as natural disasters, war, terrorism, labour disputes, government action or failures of utilities or internet providers. This does not excuse payment obligations or obligations to safeguard PHI that remain within the party’s control."],
      ["Relationship.", "The parties are independent contractors. Nothing in these Terms creates a partnership, joint venture, agency or employment relationship."],
      ["No third-party beneficiaries.", "These Terms give no rights to anyone other than the parties."],
      ["Waiver and severability.", "Failure to enforce a provision is not a waiver. If a provision is found unenforceable, it will be enforced to the maximum extent permissible and the rest of these Terms will remain in effect."],
      ["Electronic acceptance.", "Accepting these Terms electronically is as binding as signing them. Each party consents to receiving records and notices about the Service electronically."],
      ["Publicity.", "We will not use your name or logo to identify you as a customer without your written permission."],
      ["Interpretation.", "Headings are for convenience only. “Including” means “including without limitation”."],
    ),
  ),
  section(
    "contact",
    TERMS_HEADINGS,
    table({
      caption: `Contacts for the ${LEGAL_TITLES.terms}`,
      columns: ["Purpose", "Contact"],
      rows: [
        ["Legal notices", legalEmail],
        ["Privacy", privacyEmail],
        ["Security", securityEmail],
        ["Mail", `${company}, ${address}`],
      ],
    }),
  ),
];
