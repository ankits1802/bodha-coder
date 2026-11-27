import type { StatusTone } from "@/components/ui/StatusDot";
import type { HighlightTone } from "@/lib/highlight";

export const LANDING_TEXT = {
  nav: { label: "Site", how: "How it works", security: "Security", signIn: "Sign in" },
  requestDemo: "Request a demo",
  hero: {
    title: "Bill the level you can defend.",
    lead: "Bodha Coder checks every visit note against the codes you bill, too high or too low, and shows the sentence behind each change.",
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
    window: "Visit review",
    evidence: "Evidence",
    verdict: "Billed one level too high",
    adviceLead: "Bill ",
    adviceCode: "99214",
    adviceTail: ", not ",
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
  floating: ["99214", "E11.65", "I12.9", "G2211", "R20.2", "99417", "Z79.84", "N18.30", "96127", "E78.5"],
  story: {
    label: "How it works",
    acts: [
      { step: "Upload.", title: "Every note, read.", body: "Drop the day's PDFs. Each visit is read against the codes you billed." },
      {
        step: "Review.",
        title: "Every code, shown.",
        body: "Each level and code points to the sentence that supports it, checked against the code set for the date of service.",
      },
      {
        step: "Defend.",
        title: "Every answer, kept.",
        body: "Questions reach the provider as a secure link. The signed answer, every decision and a defense packet stay on record.",
      },
    ],
    upload: { file: "PDF" },
    review: [
      { phrase: "A1c up to 8.4", code: "E11.65", tone: "ok" },
      { phrase: "add amlodipine", code: "I12.9", tone: "ok" },
      { phrase: "rule out neuropathy", code: "R20.2", tone: "warn" },
    ],
    defend: { packet: "Defense packet", addendum: "Addendum", signed: "Signed" },
  },
  numbers: {
    label: "At a glance",
    items: [
      { value: "100%", label: "of suggested codes checked against the official code set" },
      { value: "Both ways", label: "billed too high and billed too low" },
      { value: "1 click", label: "to approve" },
    ],
    approve: "Approve",
    approved: "Approved",
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
