export const LOCAL_BACKEND_URL = "http://localhost:8000";

export function backendUrl(): string {
  return process.env.BACKEND_URL ?? LOCAL_BACKEND_URL;
}
