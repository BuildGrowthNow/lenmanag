import { API_BASE_URL } from "@/lib/constants";

type RequestOptions = {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
};

async function getServerCookieHeader(): Promise<string | null> {
  if (typeof window !== "undefined") {
    return null;
  }
  try {
    const nextHeaders = await import("next/headers");
    const store = nextHeaders.cookies();
    const cookieHeader = store.getAll().map((cookie) => `${cookie.name}=${cookie.value}`).join("; ");
    return cookieHeader || null;
  } catch {
    return null;
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const message = payload?.message || payload?.detail || response.statusText;
    throw new Error(message);
  }
  return payload as T;
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && options.body instanceof FormData;
  const serverCookieHeader = await getServerCookieHeader();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method || "GET",
    credentials: "include",
    headers: {
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
