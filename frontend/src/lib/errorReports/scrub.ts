import type { ErrorEvent } from "@sentry/nextjs";

export type Breadcrumb = NonNullable<ErrorEvent["breadcrumbs"]>[number];
type Exception = NonNullable<NonNullable<ErrorEvent["exception"]>["values"]>[number];
type StackFrame = NonNullable<NonNullable<Exception["stacktrace"]>["frames"]>[number];

export const REDACTED = "[redacted]";
export const SAFE_MESSAGES: ReadonlySet<string> = new Set([
  "Failed to fetch",
  "Load failed",
  "NetworkError when attempting to fetch resource.",
  "The operation was aborted.",
]);

const ID_LIKE = /\d/;
const ID_SEGMENT = ":id";
const BASE = "https://route.invalid";

export function safeText(text: string): string {
  return SAFE_MESSAGES.has(text) ? text : REDACTED;
}

export function routeOf(address: string): string {
  const parsed = parsedAddress(address);
  if (!parsed) return ID_SEGMENT;
  return parsed.pathname
    .split("/")
    .map((segment) => (ID_LIKE.test(segment) ? ID_SEGMENT : segment))
    .join("/");
}

export function withoutQuery(address: string): string {
  const parsed = parsedAddress(address);
  if (!parsed) return REDACTED;
  if (parsed.origin === "null") return address.split(/[?#]/)[0] ?? REDACTED;
  return parsed.origin === BASE ? parsed.pathname : `${parsed.origin}${parsed.pathname}`;
}

export function scrubBreadcrumb(crumb: Breadcrumb): Breadcrumb {
  return defined({ type: crumb.type, category: crumb.category, level: crumb.level, timestamp: crumb.timestamp });
}

export function scrubEvent(event: ErrorEvent): ErrorEvent {
  const kept: ErrorEvent = {
    ...defined({
      event_id: event.event_id,
      timestamp: event.timestamp,
      level: event.level,
      platform: event.platform,
      release: event.release,
      environment: event.environment,
      transaction: event.transaction ? routeOf(event.transaction) : undefined,
    }),
    type: undefined,
  };
  if (event.sdk) kept.sdk = defined({ name: event.sdk.name, version: event.sdk.version });
  if (event.message) kept.message = safeText(event.message);
  if (event.exception?.values) kept.exception = { values: event.exception.values.map(scrubException) };
  if (event.request?.url) kept.request = { url: routeOf(event.request.url) };
  if (event.breadcrumbs) kept.breadcrumbs = event.breadcrumbs.map(scrubBreadcrumb);
  return kept;
}

function scrubException(exception: Exception): Exception {
  const kept: Exception = defined({ type: exception.type, module: exception.module });
  if (exception.value) kept.value = safeText(exception.value);
  if (exception.mechanism) kept.mechanism = defined({ type: exception.mechanism.type, handled: exception.mechanism.handled });
  if (exception.stacktrace?.frames) kept.stacktrace = { frames: exception.stacktrace.frames.map(scrubFrame) };
  return kept;
}

function scrubFrame(frame: StackFrame): StackFrame {
  return defined({
    filename: frame.filename ? withoutQuery(frame.filename) : undefined,
    module: frame.module,
    function: frame.function,
    lineno: frame.lineno,
    colno: frame.colno,
    in_app: frame.in_app,
  });
}

function parsedAddress(address: string): URL | null {
  try {
    return new URL(address, BASE);
  } catch {
    return null;
  }
}

function defined<T extends object>(value: T): T {
  return Object.fromEntries(Object.entries(value).filter(([, item]) => item !== undefined)) as T;
}
