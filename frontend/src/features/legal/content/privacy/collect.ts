import { clauses, links, paragraph, section, subheading } from "../../blocks";
import { LEGAL_PARTY, SERVICE_FACTS } from "../../config";
import { LEGAL_TITLES, PRIVACY_HEADINGS } from "../headings";

const { product, company } = LEGAL_PARTY;

export const PRIVACY_COLLECT = [
  section(
    "scope",
    PRIVACY_HEADINGS,
    paragraph(
      `This ${LEGAL_TITLES.privacy} explains how ${company} (“we”, “us” or “our”) collects, uses, shares and protects personal information about visitors to our website and people who use ${product} (the “Service”) through an account.`,
    ),
    paragraph(
      `Patient information is handled differently. Visit notes and other protected health information (PHI) that our customers upload are processed on their behalf, as a business associate under HIPAA, under our ${LEGAL_TITLES.baa} and ${LEGAL_TITLES.terms} rather than under this policy. We use PHI only to provide the Service to the customer that uploaded it, as those agreements permit. If you are a patient, please contact your health care provider about your health information; we will pass on any request we receive to the customer concerned.`,
    ),
    paragraph(
      "Our customers decide who has an account in the Service. Some information about account users, such as their role and activity, is also handled for those customers under our agreements with them.",
    ),
    links("baa", "terms", "subprocessors", "security"),
  ),
  section(
    "collect",
    PRIVACY_HEADINGS,
    subheading("Information you or your organization give us"),
    clauses(
      ["Account information:", "name, work email address, practice or organization name, role and time zone, and a password, which we store only as a salted hash."],
      ["Two-step verification:", "the secret for your authenticator app, which we store encrypted, and your recovery codes, which we store only as hashes."],
      ["Provider contact details:", "for providers who answer documentation questions, the email address or mobile number the practice enters, used to send secure links and one-time codes."],
      ["Agreement records:", "when an organization signs up, the version of the Terms and BAA accepted, when, by which account and through which sign-in method."],
      ["Billing contact information:", "the billing contact’s name, email address and address, and the organization name, when you subscribe. Card and bank details are collected by our payment processors, Stripe and PayPal, and are not stored by us."],
      ["Email domains:", "the email domain a practice or organization claims so that colleagues can join it, how and when it was verified, and the admin mailbox at that domain a verification link was sent to."],
      ["Join requests:", "when you sign up with an email address at a claimed domain and ask to join that practice, your name and work email address, kept with the request so that its admins can decide."],
      ["Demo requests:", "your name, work email address, organization and message when you ask for a demonstration."],
      ["Correspondence:", "what you send us when you contact us for support or otherwise."],
    ),
    subheading("Information from sign-in services"),
    paragraph(
      "If you choose to sign in with Google, Microsoft or Yahoo, that service sends us your name, email address, whether the email address is verified, and an identifier for your account with it, using the OpenID Connect scopes “openid”, “email” and “profile”. We use these only to sign you in and to link the sign-in service to your account. We never receive your password for that service, and we do not access your contacts, files, calendar or mail.",
    ),
    subheading("Information collected automatically"),
    clauses(
      ["Access log:", `when you sign in, or open, change or export a record, the Service records who did it, the action, the time, your IP address and your browser’s user agent. Viewing or exporting the access log is recorded in it too. Customers rely on this log for HIPAA compliance, and it is kept for the period each customer chooses: ${SERVICE_FACTS.accessLogYears} years by default and up to ${SERVICE_FACTS.accessLogMaxYears}, never less than ${SERVICE_FACTS.accessLogYears}.`],
      ["Signed-in devices:", "for each device where you are signed in, the time it was last used, its IP address and browser user agent, so that you can review your devices and sign them out."],
      ["Service logs:", "technical records of each request (the type of page or action, the result, the time taken and a request identifier) and of errors, used to run and secure the Service. These logs are designed to exclude names, email addresses, IP addresses, search text and note content."],
      ["Security signals:", "counts of sign-in, password reset, sign-up and demo request attempts, stored against a one-way hash of the email address or IP address involved, used to stop abuse."],
      ["Usage timing:", "how long the steps of the work take and where they pause, used to make the Service faster: for example how long a note is open in review until it is approved or left, how many key presses and clicks each decision takes, and pauses of a minute or more with the part of the screen they happened in. Each record holds only the account, practice and role, the name of the step, times and counts; never note text, codes, patient details, free text or web addresses. Practice admins see these only as medians and ranges by role and step, and we see them only across practices. Nothing is recorded while a session is limited to billing."],
    ),
    paragraph(
      `We do not use advertising trackers or third-party analytics. See “${PRIVACY_HEADINGS.cookies}”.`,
    ),
  ),
];
