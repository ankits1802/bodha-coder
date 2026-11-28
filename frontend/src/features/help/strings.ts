export type HelpSectionKey = "upload" | "review" | "ask" | "compliance" | "billing" | "security" | "shortcuts";

export const HELP_TEXT = {
  pageTitle: "Help",
  title: "Help",
  sections: {
    upload: {
      title: "Upload notes",
      paragraphs: [
        "Drop visit-note PDFs anywhere in Bodha, or choose them on Upload notes. Bodha reads page one of each file and fills in the provider, date of service, place, patient and, when it can tell, the payer.",
        "Check each file's details and billed codes, change anything that is wrong, choose a payer when you know it, then start reading. Bodha reads every note and places it in a list.",
        "A file named date - patient - billed CPT, such as 2026-11-25 - REYES MARISOL - 99215.pdf, also fills in the patient and the billed code.",
        "Notes can also arrive by email, from a watched folder or from your EHR once an admin sets these up in Practice setup.",
        "A note is due 48 hours after its day of service ends.",
      ],
    },
    review: {
      title: "Review notes",
      paragraphs: [
        "The review queue lists open notes by due time in five lists: Ready to approve, Needs a coder, Questions to send, Waiting on provider and Compliance.",
        "Open a note to see each suggested code beside the evidence in the note. Accept or keep each suggestion and the claim updates as you decide.",
        "Approve when the claim is right. Notes whose codes already match the note can be approved together from the queue.",
        "Assign notes to yourself, or as an admin to anyone, and choose Mine to see only your notes. The daily summary email is turned on or off on your Account page, under your name in the sidebar.",
        "Search finds any note, including approved and exported ones, by patient, provider, file name or billed or final code.",
      ],
    },
    ask: {
      title: "Ask the provider",
      paragraphs: [
        "When the note needs a detail only the provider can give, choose Ask provider and edit the questions. Questions stay non-leading and never mention payment.",
        "The provider gets a secure link by email or text, confirms a one-time code, answers and signs. The answers are added to the note as an addendum and Bodha reads the note again.",
        "You can hold the claim until the provider answers. An unanswered request gets up to two reminders and its link expires after three days.",
        "A provider with several open requests can go straight to the next one after signing.",
      ],
    },
    compliance: {
      title: "Compliance",
      paragraphs: [
        "A note goes to Compliance when someone flags it, when the billed visit is two or more levels too high, or when it carries a critical audit risk.",
        "Confirm the suggested code, return the note to the coder, or keep the billed level with a reason. The person who flagged a note cannot clear it.",
      ],
    },
    billing: {
      title: "Billing",
      paragraphs: [
        "Billing, Ready to bill lists approved claims. Download them as a CSV file for your billing system, or, once your practice has connected a clearinghouse, send them as 837P claim files or download the 837P file. Every download and submission is recorded.",
        "A claim the clearinghouse or payer rejects comes back to Ready to bill with the reason, so it can be fixed and sent again.",
        "An approved note can be reopened until it has been exported or sent.",
      ],
    },
    security: {
      title: "Two-step verification and recovery codes",
      paragraphs: [
        "Some roles sign in with a six-digit code from an authenticator app as well as a password.",
        "When you set up two-step verification you get ten recovery codes. Each one works once in place of the six-digit code. Keep them somewhere safe.",
        "Make new recovery codes on your Account page with a current six-digit code. The old codes stop working.",
        "If you lose both your device and your codes, ask an admin to reset your two-step verification.",
      ],
    },
    shortcuts: {
      title: "Keyboard shortcuts",
      paragraphs: ["Press ? on any screen to see the shortcuts for that screen."],
    },
  } satisfies Record<HelpSectionKey, { title: string; paragraphs: readonly string[] }>,
} as const;
