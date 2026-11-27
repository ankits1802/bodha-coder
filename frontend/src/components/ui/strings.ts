export const UI_TEXT = {
  select: {
    search: "Search",
    noMatches: "No matches",
  },
  date: {
    choose: "Choose date",
    chooseFor: (label: string) => `Choose ${label.toLowerCase()}`,
    previousMonth: "Previous month",
    nextMonth: "Next month",
    month: "Month",
    year: "Year",
    today: "Today",
  },
} as const;
