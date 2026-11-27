export const PRACTICE_TEXT = {
  leave: "Leave",
  leaveFor: (name: string) => `Leave ${name}`,
  leaveItem: (name: string) => `Leave ${name}…`,
  confirmTitle: (name: string) => `Leave ${name}?`,
  cancel: "Cancel",
  newPractice: "New practice",
  choice: (name: string, role: string) => `${name} · ${role}`,
} as const;
