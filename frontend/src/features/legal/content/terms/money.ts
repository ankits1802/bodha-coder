import { clauses, paragraph, section } from "../../blocks";
import { LEGAL_PARTY, LEGAL_PERIODS } from "../../config";
import { TERMS_HEADINGS } from "../headings";

const { refundPolicy } = LEGAL_PARTY;

export const TERMS_MONEY = [
  section(
    "fees",
    TERMS_HEADINGS,
    clauses(
      ["Pricing.", "Paid plans are charged per Active Provider, monthly or annually, at the prices shown on our pricing page or in your Order when you subscribe. Enterprise plans are priced in an Order."],
      ["Payment.", `You authorize us, and our payment processors Stripe and PayPal, to charge the payment method you provide for all fees when due. Fees for each period are charged in advance. Active Providers added during a period may be charged for the rest of that period, as described on our pricing page. Invoiced fees are due within ${LEGAL_PERIODS.invoiceDays} days of the invoice date unless your Order says otherwise.`],
      ["Automatic renewal.", "Paid subscriptions renew automatically for successive periods of the same length, monthly or annual, unless you cancel before the end of the current period. Where the law requires it, we will remind you before an annual subscription renews."],
      ["Cancellation.", "You may cancel at any time in the Service’s billing settings or by writing to us. Cancellation takes effect at the end of the current paid period, and you keep access until then."],
      ["Refunds.", refundPolicy],
      ["Taxes.", "Fees do not include taxes. You are responsible for sales, use, value-added and similar taxes on your purchase, other than taxes on our net income. Where we must collect them, we will add them to your invoice unless you give us a valid exemption certificate."],
      ["Price changes.", `We may change prices for future periods by giving you at least ${LEGAL_PERIODS.priceNoticeDays} days’ notice by email or in the Service. A change applies from your first renewal after the notice period. If you do not agree, you may cancel before it takes effect.`],
      ["Late payment.", `If a payment fails or is overdue, we will tell you. If it remains unpaid ${LEGAL_PERIODS.paymentNoticeDays} days after that notice, we may suspend the Service until it is paid. Suspension for non-payment does not delete Customer Data.`],
      ["Billing disputes.", `If you dispute a charge in good faith, tell us within ${LEGAL_PERIODS.disputeDays} days of the charge and pay any undisputed amount. We will work with you to resolve it promptly.`],
    ),
    paragraph(
      "Payment processors receive only the billing contact details, practice or organization name and payment information needed to take payment. We never send PHI to payment processors. Card and bank account details are entered with the processor and are not stored by us.",
    ),
  ),
];
