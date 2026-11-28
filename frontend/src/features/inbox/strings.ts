export const INBOX_TEXT = {
  title: "Inbox",
  unreadCount: (count: string) => `${count} unread`,
  markAllRead: "Mark all read",
  listLabel: "Inbox items",
  unread: "Unread",
  loading: "Loading inbox",
  empty: "Nothing here",
  retry: "Try again",
  meta: (patient: string, day: string) => `${patient} · ${day}`,
  sentences: {
    providerAnswered: (actor: string, questions: number) =>
      questions === 1 ? `${actor} answered 1 question` : `${actor} answered ${questions} questions`,
    levelDisagreed: (actor: string) => `${actor} disagreed with a visit level you approved`,
    requestExpired: "A provider request expired",
    levelRequestExpired: "A visit level request expired",
    mentioned: (actor: string) => `${actor} mentioned you`,
    trainingAssigned: (actor: string, notes: number) =>
      notes === 1 ? `${actor} assigned you 1 training note` : `${actor} assigned you ${notes} training notes`,
    paymentFailed: (day: string) => `Payment failed. Access continues until ${day}`,
    planEnding: (day: string) => `The plan ends on ${day}`,
    complianceReturned: (actor: string, reason: string | null) => (reason ? `${actor} returned a note: ${reason}` : `${actor} returned a note`),
    joinRequested: (actor: string) => `${actor} asked to join`,
    claimsRejected: (claims: number) => (claims === 1 ? "A claim was rejected" : `${claims} claims were rejected`),
  },
} as const;
