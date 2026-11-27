import { getSession, subscribeSession } from "@/lib/session/store";

interface Entry {
  data: unknown;
  expires: number;
}

export const PREFETCH_SECONDS = 60;
export const LOOKUP_SECONDS = 300;

const entries = new Map<string, Entry>();
const loading = new Map<string, Promise<unknown>>();

subscribeSession(() => {
  if (getSession().user === null) {
    entries.clear();
    loading.clear();
  }
});

export function readRemote<T>(key: string, now = Date.now()): T | undefined {
  const entry = entries.get(key);
  if (!entry) return undefined;
  if (entry.expires <= now) {
    entries.delete(key);
    return undefined;
  }
  return entry.data as T;
}

export function keepRemote<T>(key: string, data: T, seconds: number, now = Date.now()): void {
  entries.set(key, { data, expires: now + seconds * 1000 });
}

export function writeRemote<T>(key: string, data: T): void {
  const entry = entries.get(key);
  if (entry) entries.set(key, { ...entry, data });
}

export function editRemote<T>(key: string, edit: (data: T) => T): void {
  const entry = entries.get(key);
  if (entry) entries.set(key, { ...entry, data: edit(entry.data as T) });
}

export function forgetRemote(key: string): void {
  entries.delete(key);
}

export function loadRemote<T>(key: string, load: () => Promise<T>, keepSeconds: number, join = true): Promise<T> {
  const pending = join ? (loading.get(key) as Promise<T> | undefined) : undefined;
  if (pending) return pending;
  const started = load().then((data) => {
    if (keepSeconds > 0) keepRemote(key, data, keepSeconds);
    return data;
  });
  loading.set(key, started);
  const settle = () => {
    if (loading.get(key) === started) loading.delete(key);
  };
  started.then(settle, settle);
  return started;
}

export function prefetchRemote<T>(key: string, load: () => Promise<T>, seconds = PREFETCH_SECONDS): void {
  if (readRemote(key) !== undefined || loading.has(key)) return;
  loadRemote(key, load, seconds).catch(() => undefined);
}
