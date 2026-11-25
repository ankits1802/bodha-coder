import type { SignedIn, User } from "@/lib/api/types";

export interface SessionState {
  accessToken: string | null;
  user: User | null;
}

const EMPTY: SessionState = { accessToken: null, user: null };

let state: SessionState = EMPTY;
const listeners = new Set<() => void>();

function emit(): void {
  for (const listener of listeners) listener();
}

export function getSession(): SessionState {
  return state;
}

export function getServerSession(): SessionState {
  return EMPTY;
}

export function getAccessToken(): string | null {
  return state.accessToken;
}

export function setSession(signedIn: SignedIn): void {
  state = { accessToken: signedIn.access_token, user: signedIn.user };
  emit();
}

export function clearSession(): void {
  state = EMPTY;
  emit();
}

export function subscribeSession(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
