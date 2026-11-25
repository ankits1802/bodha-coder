import { API_MESSAGES } from "./messages";

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

interface ValidationDetail {
  msg?: unknown;
}

function validationMessage(detail: unknown): string | null {
  if (!Array.isArray(detail)) return null;
  const messages = detail
    .map((item: ValidationDetail) => (typeof item?.msg === "string" ? item.msg : null))
    .filter((item): item is string => item !== null);
  return messages.length > 0 ? messages.join("; ") : null;
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

export async function errorFromResponse(response: Response): Promise<ApiError> {
  const body: unknown = await response.json().catch(() => null);
  if (body && typeof body === "object") {
    const record = body as Record<string, unknown>;
    if (typeof record.message === "string") {
      const code = typeof record.error === "string" ? record.error : "error";
      return new ApiError(response.status, code, record.message);
    }
    const detail = validationMessage(record.detail);
    if (detail) return new ApiError(response.status, "invalid", detail);
  }
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
