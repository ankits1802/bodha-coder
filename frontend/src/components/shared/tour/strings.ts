import type { TourKey } from "@/lib/api/types";

export type TourExtra = "decide" | "evidence" | "ask" | "accessLog";

export const TOUR_TEXT = {
  take: "Take the tour",
  next: "Next",
  back: "Back",
  done: "Done",
  skip: "Skip tour",
  count: (step: number, total: number) => `${step} of ${total}`,
  announce: (count: string, title: string, line: string) => `${count}. ${title}. ${line}`,
  announceHighlighted: (count: string, title: string, line: string) => `${count}. ${title}, highlighted. ${line}`,
  welcome: {
    practice: { title: "Welcome to Bodha Assure", line: "A quick look at everything you can open." },
    hq: { title: "Welcome to Bodha Assure", line: "A quick look at the HQ console." },
  } satisfies Record<TourKey, { title: string; line: string }>,
  areas: {
    today: "Notes due today and what to review next.",
    upload: "Add visit-note PDFs with the codes you billed.",
    queue: "Every open note, sorted into lanes by due time.",
    compliance: "Notes held for a compliance decision.",
    billing: "Approved claims, ready to export for billing.",
    remittances: "Payer remittances matched to your claims.",
    training: "Practice sets that score your coding.",
    insights: "Volumes, outcomes and turnaround for the practice.",
    quality: "Blind audits and measured accuracy.",
    setup: "Providers, payers, places and checks for your practice.",
    team: "Invite people and choose their roles.",
    plan: "Your plan, seats and payment.",
    security: "Two-step sign-in, devices and recovery codes.",
    hqOverview: "Practices that need attention.",
    hqPractices: "Add, renew, block or remove practices.",
    hqSpend: "AI cost per practice and provider.",
    hqActivity: "Every HQ action, by person and day.",
    hqDemos: "Demo requests from the website.",
    hqTeam: "Invite and manage HQ accounts.",
    hqSecurity: "Your two-step sign-in and devices.",
    search: "Find any note by patient, provider, file or code.",
    help: "Guides and the shortcuts for your role.",
  } as Readonly<Record<string, string>>,
  extras: {
    decide: { title: "Accept or keep", line: "Press Y to accept a change, N to keep the billed code." },
    evidence: { title: "Evidence", line: "Each change quotes the sentence in the note behind it." },
    ask: { title: "Questions", line: "Ask the provider from the Questions tab when detail is missing." },
    accessLog: { title: "Access log", line: "Who opened, changed or exported each note." },
  } satisfies Record<TourExtra, { title: string; line: string }>,
  replay: { title: "Take the tour again", line: "Replay it any time from here." },
} as const;
