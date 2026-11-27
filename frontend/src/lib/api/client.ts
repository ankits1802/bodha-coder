import { clearSession, getAccessToken, setSession } from "@/lib/session/store";
import { ApiError, errorFromResponse } from "./errors";
import { API_MESSAGES } from "./messages";
import type { SignedIn } from "./types";

export type Auth = "session" | "none" | { bearer: string };
export type QueryValue = string | number | boolean | undefined | null;
type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

export interface RequestOptions {
  method?: Method;
  body?: unknown;
  form?: FormData;
  query?: Record<string, QueryValue>;
  auth?: Auth;
}

export interface DownloadedFile {
  blob: Blob;
  fileName: string | null;
}

export const SIGN_IN_PATH = "/sign-in";
const REFRESH_PATH = "/api/auth/refresh";
const PLAN_ENDED = "plan_ended";

let sessionEndedHandler: () => void = () => {
  window.location.replace(SIGN_IN_PATH);
};
let refreshing: Promise<boolean> | null = null;

export function onSessionEnded(handler: () => void): void {
  sessionEndedHandler = handler;
}

export function endSession(): void {
  clearSession();
  sessionEndedHandler();
}

export function urlFor(path: string, query?: Record<string, QueryValue>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  const search = params.toString();
  return search ? `${path}?${search}` : path;
}

function tokenFor(auth: Auth): string | null {
  if (auth === "session") return getAccessToken();
  if (auth === "none") return null;
  return auth.bearer;
}

function send(path: string, options: RequestOptions, auth: Auth): Promise<Response> {
  const headers = new Headers({ Accept: "application/json" });
  const token = tokenFor(auth);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let body: BodyInit | undefined;
  if (options.form) {
    body = options.form;
  } else if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.body);
  }
  const method = options.method ?? (body === undefined ? "GET" : "POST");
  return fetch(urlFor(path, options.query), { method, headers, body, credentials: "same-origin", cache: "no-store" });
}

async function performRefresh(): Promise<boolean> {
  const response = await fetch(REFRESH_PATH, { method: "POST", credentials: "same-origin", cache: "no-store" });
  if (!response.ok) return false;
  setSession((await response.json()) as SignedIn);
  return true;
}

export function refreshSession(): Promise<boolean> {
  refreshing ??= performRefresh().finally(() => {
    refreshing = null;
  });
  return refreshing;
}

async function refusedForEndedPlan(response: Response): Promise<boolean> {
  if (response.status !== 403) return false;
  const body = (await response
    .clone()
    .json()
    .catch(() => null)) as { error?: unknown } | null;
  return body?.error === PLAN_ENDED;
}

async function authorised(path: string, options: RequestOptions): Promise<Response> {
  const auth = options.auth ?? "session";
  const response = await send(path, options, auth);
  if (auth === "session" && (await refusedForEndedPlan(response)) && !(await refreshSession())) endSession();
  if (response.status !== 401 || auth !== "session") return response;
  if (await refreshSession()) {
    const retried = await send(path, options, auth);
    if (retried.status !== 401) return retried;
  }
  endSession();
  throw new ApiError(401, "unauthorized", API_MESSAGES.signInAgain);
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await authorised(path, options);
  if (!response.ok) throw await errorFromResponse(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function requestNothing(path: string, options: RequestOptions = {}): Promise<void> {
  const response = await authorised(path, options);
  if (!response.ok) throw await errorFromResponse(response);
}

function fileNameFrom(disposition: string | null): string | null {
  const marker = "filename=";
  const start = disposition ? disposition.indexOf(marker) : -1;
  if (!disposition || start < 0) return null;
  const value = disposition.slice(start + marker.length).split(";")[0] ?? "";
  return value.replaceAll('"', "").trim() || null;
}

export async function requestFile(path: string, options: RequestOptions = {}): Promise<DownloadedFile> {
  const response = await authorised(path, options);
  if (!response.ok) throw await errorFromResponse(response);
  return { blob: await response.blob(), fileName: fileNameFrom(response.headers.get("Content-Disposition")) };
}
