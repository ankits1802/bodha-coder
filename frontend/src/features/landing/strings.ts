import type { StatusTone } from "@/components/ui/StatusDot";
import type { HighlightTone } from "@/lib/highlight";

export const LANDING_TEXT = {
  nav: { label: "Site", how: "How it works", security: "Security", signIn: "Sign in" },
  requestDemo: "Request a demo",
  hero: {
    title: "Every note, checked.",
    lead: "Bodha Coder reads each visit note and shows your coders exactly what to bill.",
    signIn: "Sign in ›",
  },
  product: {
    label: "Product preview",
    noteLabel: "Visit note · 25 Nov",
    note: "Type 2 diabetes with hyperglycemia, A1c up to 8.4. Increase metformin. Hypertension, above goal; add amlodipine. CKD, stable. Foot tingling, rule out neuropathy.",
    marks: [
      { quote: "CKD, stable", tone: "warn" as HighlightTone },
      { quote: "rule out neuropathy", tone: "bad" as HighlightTone },
    ],
    verdict: "Billed one level too high",
    advice: "Bill 99214, not ",
    struck: "99215",
    changedLabel: "changes to",
    addedLabel: "add",
    rows: [
      { before: "E11.9", after: "E11.65", status: "Supported", tone: "ok" as StatusTone },
      { before: "I10", after: "I12.9", status: "Supported", tone: "ok" as StatusTone },
      { before: "N18.30", after: null, status: "Ask provider", tone: "warn" as StatusTone },
      { before: "R20.2", after: null, status: "Add", tone: "ok" as StatusTone },
    ],
  },
  how: {
    title: "Upload. Review. Bill.",
    features: [
      { title: "Reads every note.", body: "Drop the day's PDFs. Patient, date and billed code are taken from each file." },
      { title: "Explains every code.", body: "Each suggestion points to the sentence in the note that supports it." },
      { title: "Asks the provider.", body: "Questions go out as a secure link. The answer comes back as a signed addendum." },
    ],
  },
  numbers: {
    label: "At a glance",
    items: [
      { value: "3,000", label: "notes a day" },
      { value: "48 h", label: "from visit to ready to bill" },
      { value: "1 click", label: "to approve" },
    ],
  },
  security: {
    title: "Private by design.",
    lead: "Patient details stay where they belong.",
    items: [
      "Two-step verification",
      "Every note opened, changed or exported is logged",
      "Encrypted documents, short-lived links",
      "No patient details in messages",
      "Automatic sign-out",
    ],
  },
  demo: { title: "See it on your notes." },
  footer: { copyright: "© 2026 Bodha", label: "Footer", security: "Security", signIn: "Sign in" },
  form: {
    title: "Request a demo",
    name: "Name",
    email: "Work email",
    organization: "Practice or organization",
    message: "Message",
    optional: "optional",
    submit: "Send request",
    cancel: "Cancel",
    close: "Close",
    sent: "Thanks. We will be in touch.",
    required: "Required",
    invalidEmail: "Enter a valid email.",
  },
} as const;
