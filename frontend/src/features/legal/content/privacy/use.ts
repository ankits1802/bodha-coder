import { bullets, paragraph, section, table } from "../../blocks";
import { SERVICE_FACTS } from "../../config";
import { PRIVACY_HEADINGS } from "../headings";

export const PRIVACY_USE = [
  section(
    "use",
    PRIVACY_HEADINGS,
    paragraph("We use personal information to:"),
    bullets(
      "provide, operate and support the Service and your account;",
      "sign you in, protect accounts with two-step verification and rate limits, detect and prevent abuse, and keep the Service secure;",
      "send service messages, such as invitations, password resets, sign-in codes, daily summaries and secure links for provider questions;",
      "take payment, keep billing records and manage subscriptions;",
      "respond to demo requests, support requests and other enquiries;",
      "understand and improve the Service using aggregated information that does not identify you;",
      "record which agreements an organization accepted, comply with the law, and enforce our terms.",
    ),
    paragraph(
      "We do not sell personal information, share it for cross-context behavioral advertising, or use it for targeted advertising. We do not make decisions about people that have legal or similarly significant effects solely by automated means.",
    ),
    paragraph(
      "Service messages are part of using the Service and continue while you have an account. If we send you marketing email, it will include a way to opt out at any time.",
    ),
  ),
  section(
    "bases",
    PRIVACY_HEADINGS,
    paragraph(
      "Where the law requires a legal basis for using personal information, for example if you visit our website from the European Economic Area or the United Kingdom, we rely on: performance of a contract, to provide the Service and your account; our legitimate interests, to secure, support, improve and promote the Service and to answer enquiries, which we balance against your rights; compliance with legal obligations, such as keeping records and answering lawful requests; and consent, where we ask for it, which you may withdraw at any time.",
    ),
  ),
  section(
    "cookies",
    PRIVACY_HEADINGS,
    paragraph(
      "We use only cookies and browser storage that are strictly necessary for the Service to work and stay secure. Our website and the Service contain no advertising cookies, third-party analytics or tracking scripts, social media pixels or third-party cookies, and their content security policy blocks scripts from other sites.",
    ),
    table({
      caption: "Cookies and browser storage we use",
      columns: ["Name", "Purpose", "How long"],
      rows: [
        ["bodha_refresh", "Keeps you signed in on this device. Sent only to the sign-in service of the Service.", `Up to ${SERVICE_FACTS.refreshDays} days; ends after ${SERVICE_FACTS.sessionIdleMinutes} minutes without use or when you sign out`],
        ["bodha_oidc", "Protects sign-in with Google, Microsoft or Yahoo against forgery.", `${SERVICE_FACTS.oidcCookieMinutes} minutes`],
        ["bodha_signup", "Holds the identity a sign-in service returned while you finish creating a practice.", `${SERVICE_FACTS.signupCookieMinutes} minutes`],
        ["Browser local storage", "Remembers interface preferences, such as a collapsed sidebar and your last queue filters. Holds identifiers and choices only, never search text or patient details.", "Until you clear it"],
      ],
    }),
    paragraph(
      "These cookies are set by us, are marked HttpOnly so page scripts cannot read them, and are sent only over secure connections. Because we use only strictly necessary technologies, we do not show a cookie banner. We do not track you across other websites, so we do not respond differently to Do Not Track signals; we treat a Global Privacy Control signal as a request to opt out of the sale or sharing of personal information, which we do not do in any case.",
    ),
  ),
];
