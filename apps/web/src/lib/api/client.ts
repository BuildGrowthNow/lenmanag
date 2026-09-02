import { API_BASE_URL } from "@/lib/constants";

export const API_VERSION = "1";
export const VERSION_HEADER_NAME = "X-API-Version";
const VERSIONED_PATH_PREFIX = `/api/v${API_VERSION}`;
export const VENDOR_MEDIA_TYPE = `application/vnd.lenmanag.v${API_VERSION}+json`;

type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
};

export function versionedPath(path: string): string {
  return normalizePath(path);
}

type ApiResponseEnvelope<T> = {
  status: "success" | "error";
  meta: { version: string; requestId: string; generatedAt: string };
  data?: T;
  error?: { code: string; message: string; details?: Record<string, unknown> };
};

function readableError(value: unknown, fallback: string): string {
  if (typeof value === "string" && value.trim()) return value;
  if (Array.isArray(value)) {
    const messages = value
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item && typeof item.msg === "string") return item.msg;
        return null;
      })
      .filter((message): message is string => Boolean(message));
    if (messages.length) return messages.join("; ");
  }
  if (value && typeof value === "object" && "message" in value && typeof value.message === "string") {
    return value.message;
  }
  return fallback;
}

function normalizePath(path: string): string {
  if (!path.startsWith("/api")) {
    return path;
  }
  if (path.startsWith(`${VERSIONED_PATH_PREFIX}`)) {
    return path;
  }
  if (path === "/api") {
    return VERSIONED_PATH_PREFIX;
  }
  if (path.startsWith("/api/")) {
    const remainder = path.slice(5);
    if (remainder.startsWith("v")) {
      return `/api/${remainder}`;
    }
    return `${VERSIONED_PATH_PREFIX}/${remainder}`;
  }
  return path;
}

async function parseResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  let payload: ApiResponseEnvelope<T> | null = null;
  try {
    payload = text ? JSON.parse(text) : null;
  } catch {
    throw new Error(response.ok ? "The API returned an invalid response." : response.statusText);
  }
  if (!response.ok) {
    const raw = payload as ApiResponseEnvelope<T> & { detail?: unknown; error?: unknown };
    throw new Error(
      readableError(raw.error, readableError(raw.detail, response.statusText))
    );
  }
  if (!payload || payload.status !== "success") {
    throw new Error(readableError(payload?.error, "Unknown API error."));
  }
  return payload.data as T;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const normalizedPath = normalizePath(path);

  let authToken: string | null = null;
  if (typeof window !== "undefined") {
    authToken = localStorage.getItem("access_token");
  }

  const response = await fetch(`${API_BASE_URL}${normalizedPath}`, {
    method: options.method || "GET",
    headers: {
      Accept: VENDOR_MEDIA_TYPE,
      [VERSION_HEADER_NAME]: API_VERSION,
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      ...(options.headers || {})
    },
    body:
      options.body === undefined
        ? undefined
        : isFormData
          ? (options.body as BodyInit)
          : JSON.stringify(options.body)
  });
  return parseResponse<T>(response);
}

export async function safeRequest<T>(path: string, fallback: T, options: RequestOptions = {}): Promise<T> {
  try {
    return await request<T>(path, options);
  } catch (error) {
    console.error(`[API Client] Request failed for ${path}:`, error instanceof Error ? error.message : String(error));
    return fallback;
  }
}
