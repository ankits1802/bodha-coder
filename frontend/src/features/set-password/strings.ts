export const SET_PASSWORD_TEXT = {
  pageTitle: "Set password",
  title: "Choose a password",
  password: "New password",
  confirm: "Confirm password",
  tooShort: (length: number) => `Use at least ${length} characters.`,
  mismatch: "The passwords do not match.",
  submit: "Set password",
  entering: "Opening Bodha Assure",
  invalidLink: "This link is no longer valid.",
  newLink: "Get a new link",
  loading: "Loading",
} as const;
