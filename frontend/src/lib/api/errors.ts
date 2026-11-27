import { API_MESSAGES } from "./messages";
import type { ErrorBody } from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function fallbackMessage(status: number): string {
  return API_MESSAGES.byStatus[status] ?? API_MESSAGES.unexpected;
}

export class UserFacingError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "UserFacingError";
  }
}

function isErrorBody(body: unknown): body is ErrorBody {
  if (!body || typeof body !== "object") return false;
  const record = body as Record<string, unknown>;
  return typeof record.error === "string" && typeof record.message === "string";
}

export async function errorFromResponse(response: Response): Promise<ApiError> {
  const body: unknown = await response.json().catch(() => null);
  if (isErrorBody(body)) return new ApiError(response.status, body.error, body.message);
  return new ApiError(response.status, "error", fallbackMessage(response.status));
}

function sentence(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function messageOf(error: unknown): string {
  if (error instanceof ApiError) return sentence(error.message);
  if (error instanceof UserFacingError) return error.message;
  if (error instanceof TypeError) return API_MESSAGES.network;
  return API_MESSAGES.unexpected;
}
