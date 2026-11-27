export const VERIFY_DOMAIN_TEXT = {
  pageTitle: "Confirm email domain",
  title: "Confirm email domain",
  confirm: "Confirm domain",
  loading: "Loading",
  invalidLink: "This link has expired.",
  verified: (domain: string, practice: string) => `${domain} is confirmed for ${practice}`,
} as const;
