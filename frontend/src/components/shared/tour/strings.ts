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
    billing: "Approved claims to export, and payer remittances.",
    insights: "Volumes and outcomes, blind audits and measured accuracy.",
    settings: "Providers, payers, checks, team, plan and security.",
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
  replay: {
    practice: { title: "Your account", line: "Devices, recovery codes, practices, this tour and sign out." },
    hq: { title: "Your account", line: "Replay this tour or sign out from here." },
  } satisfies Record<TourKey, { title: string; line: string }>,
} as const;
