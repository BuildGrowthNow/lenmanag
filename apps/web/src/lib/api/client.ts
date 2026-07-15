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

async function getServerCookieHeader(): Promise<string | null> {
  if (typeof window !== "undefined") {
    return null;
  }
  try {
    const { cookies } = await import("next/headers");
    const cookieStore = await cookies();
    const allCookies = cookieStore.getAll();
    const cookieHeader = allCookies
      .map((cookie) => `${cookie.name}=${cookie.value}`)
      .join("; ");
    if (cookieHeader) {
      console.log("[API Client] Server cookies found:", allCookies.map(c => c.name).join(", "));
    } else {
      console.log("[API Client] No server cookies found");
    }
    return cookieHeader || null;
  } catch (error) {
    console.error("[API Client] Failed to get server cookies:", error);
    return null;
  }
}

type ApiResponseEnvelope<T> = {
  status: "success" | "error";
  meta: { version: string; requestId: string; generatedAt: string };
  data?: T;
  error?: { code: string; message: string; details?: Record<string, unknown> };
};

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
  const payload: ApiResponseEnvelope<T> | null = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const message = payload?.error?.message || payload?.error?.code || (payload as unknown as { detail?: string })?.detail || response.statusText;
    throw new Error(message);
  }
  if (!payload || payload.status !== "success") {
    const message = payload?.error?.message || "Unknown API error.";
    throw new Error(message);
  }
  return payload.data as T;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const serverCookieHeader = await getServerCookieHeader();
  const normalizedPath = normalizePath(path);
  const response = await fetch(`${API_BASE_URL}${normalizedPath}`, {
    method: options.method || "GET",
    credentials: "include",
    headers: {
      Accept: VENDOR_MEDIA_TYPE,
      [VERSION_HEADER_NAME]: API_VERSION,
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(serverCookieHeader ? { Cookie: serverCookieHeader } : {}),
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
  } catch {
    return fallback;
  }
}
