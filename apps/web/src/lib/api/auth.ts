import { safeRequest } from "@/lib/api/client";
import type { SessionResponse } from "@/lib/types";

export async function getSession(): Promise<SessionResponse> {
  return safeRequest<SessionResponse>("/api/auth/session", {
    authenticated: false,
    user: null,
    status: "inactive",
    expiresAt: null
  });
}

export async function login(email: string, name?: string) {
  return safeRequest("/api/auth/login", { authenticated: false, status: "denied", message: "Auth service unavailable." }, {
    method: "POST",
    body: { email, name }
  });
}

export async function logout() {
  return safeRequest("/api/auth/logout", { status: "logged_out" }, { method: "POST" });
}

