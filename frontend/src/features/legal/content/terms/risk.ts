import { clauses, notice, paragraph, section } from "../../blocks";
import { LEGAL_PARTY, LEGAL_PERIODS } from "../../config";
import { LEGAL_TITLES, TERMS_HEADINGS } from "../headings";

const { liabilityCap } = LEGAL_PARTY;

export const TERMS_RISK = [
  section(
    "warranties",
    TERMS_HEADINGS,
    clauses(
      ["Mutual.", "Each party warrants that it has the authority to enter into these Terms."],
      ["Our warranty.", `We warrant that during a paid Subscription Term the Service will perform materially as described in the Documentation. If it does not, tell us with details. Your exclusive remedy, and our entire liability, is for us to use reasonable efforts to correct the problem and, if we cannot do so within ${LEGAL_PERIODS.cureDays} days of your notice, for either party to terminate the affected subscription and for us to refund prepaid fees for the rest of its term.`],
      ["Your warranty.", "You warrant that you have the rights, consents and authorizations needed to submit Customer Data to the Service, and that your use of the Service will comply with the law."],
    ),
    notice(
      "Except as expressly stated in these Terms, the Service and all Output are provided “as is” and “as available”. To the maximum extent permitted by law, we disclaim all other warranties, whether express, implied or statutory, including warranties of merchantability, fitness for a particular purpose, title, non-infringement and accuracy. We do not warrant that Output will be accurate or complete, that any claim will be paid or will withstand audit, or that the Service will be uninterrupted or error-free.",
    ),
  ),
  section(
    "liability",
    TERMS_HEADINGS,
    notice(
      "To the maximum extent permitted by law, neither party will be liable to the other for any indirect, incidental, special, consequential, exemplary or punitive damages, or for lost profits, revenue, reimbursement or goodwill, however caused and even if advised of their possibility.",
    ),
    notice(
      `To the maximum extent permitted by law, each party’s total liability arising out of or relating to these Terms and the BAA, whether in contract, tort or otherwise, will not exceed ${liabilityCap}.`,
    ),
    paragraph(
      `These exclusions and limits do not apply to your obligation to pay fees, to either party’s obligations under “${TERMS_HEADINGS.indemnities}”, to a party’s gross negligence, wilful misconduct or fraud, or to your breach of “${TERMS_HEADINGS.compliance}” or the ${LEGAL_TITLES["acceptable-use"]}. They apply even if a limited remedy fails of its essential purpose, and they reflect an allocation of risk that is part of our prices.`,
    ),
  ),
  section(
    "indemnities",
    TERMS_HEADINGS,
    clauses(
      ["By us.", "We will defend you against any claim by a third party alleging that the Service, as we provide it, infringes that party’s United States patent, copyright or trademark or misappropriates its trade secret, and will pay the damages and costs finally awarded against you or agreed by us in settlement. If such a claim is made or appears likely, we may get you the right to keep using the Service, modify it so it no longer infringes, or, if neither is commercially reasonable, terminate the affected subscription and refund prepaid fees for the rest of its term. We have no obligation for claims arising from Customer Data, from Output that you have modified, from combinations with anything we did not provide, or from use in breach of these Terms. This paragraph states our entire liability for intellectual property claims."],
      ["By you.", "You will defend us and our affiliates, officers and employees against any claim by a third party, including a government agency or payer, arising from Customer Data or your lack of rights to submit it; from claims you submitted to any payer or the coding and billing decisions behind them; or from your use of the Service in breach of these Terms, the law or our policies; and you will pay the damages, fines and costs finally awarded or agreed by you in settlement."],
      ["Procedure.", "The party seeking defense must notify the other party promptly, give it sole control of the defense and settlement, and cooperate reasonably at its expense. No settlement may impose an admission or a non-monetary obligation on the defended party without its consent."],
    ),
  ),
];
