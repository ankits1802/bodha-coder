export const PLAN_BANNER_TEXT = {
  trialLeft: (days: number) => {
    if (days === 0) return "Your trial ends today";
    if (days === 1) return "Your trial ends tomorrow";
    return `Your trial ends in ${days} days`;
  },
  pastDue: (day: string) => `Payment failed. Access continues until ${day}`,
  choosePlan: "Choose a plan",
  fixPayment: "Update payment",
  dismiss: "Hide until tomorrow",
} as const;
