import { ApiError } from "@/lib/api/errors";

export async function watchExpiry<T>(pending: Promise<T>, onExpired: () => void): Promise<T> {
  try {
    return await pending;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) onExpired();
    throw error;
  }
}
