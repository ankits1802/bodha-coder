export const API_MESSAGES = {
  network: "Can't reach Bodha Coder. Check your connection and try again.",
  signInAgain: "Sign in again",
  unexpected: "Something went wrong. Try again.",
  byStatus: {
    400: "That request was not accepted.",
    401: "Sign in again",
    403: "Your role can't do this.",
    404: "Not found.",
    409: "This changed in the meantime. Reload and try again.",
    413: "That file is too large.",
    422: "Check the highlighted details and try again.",
    429: "Too many attempts. Wait a moment and try again.",
    503: "Bodha Coder is busy. Try again in a moment.",
  } as Record<number, string>,
} as const;
