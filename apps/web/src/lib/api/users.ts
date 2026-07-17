const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface UserResponse {
  id: string;
  email: string;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

export interface SignupPayload {
  email: string;
  password: string;
  signup_code: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export async function signup(payload: SignupPayload): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/api/v1/users/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const json = await res.json();

  if (!res.ok) {
    throw new Error(json.detail || "Signup failed");
  }

  if (json.data?.access_token) {
    localStorage.setItem("access_token", json.data.access_token);
  }

  return json.data;
}

export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const res = await fetch(`${API_BASE}/api/v1/users/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const json = await res.json();

  if (!res.ok) {
    throw new Error(json.detail || "Login failed");
  }

  if (json.data?.access_token) {
    localStorage.setItem("access_token", json.data.access_token);
  }

  return json.data;
}

export async function verifyEmail(token: string): Promise<{ message: string; email: string }> {
  const res = await fetch(`${API_BASE}/api/v1/users/verify-email`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token }),
  });

  const json = await res.json();

  if (!res.ok) {
    throw new Error(json.detail || "Verification failed");
  }

  return json.data;
}

export async function resendVerification(email: string): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/api/v1/users/resend-verification`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });

  const json = await res.json();

  if (!res.ok) {
    throw new Error(json.detail || "Resend failed");
  }

  return json.data;
}

export async function forgotPassword(email: string): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/api/v1/users/forgot-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });

  const json = await res.json();

  if (!res.ok) {
    throw new Error(json.detail || "Request failed");
  }

  return json.data;
}

export async function resetPassword(token: string, newPassword: string): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/api/v1/users/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password: newPassword }),
  });

  const json = await res.json();

  if (!res.ok) {
    throw new Error(json.detail || "Reset failed");
  }

  return json.data;
}

export async function getCurrentUser(): Promise<UserResponse> {
  const token = localStorage.getItem("access_token");

  if (!token) {
    throw new Error("No authentication token");
  }

  const res = await fetch(`${API_BASE}/api/v1/users/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  const json = await res.json();

  if (!res.ok) {
    localStorage.removeItem("access_token");
    throw new Error(json.detail || "Failed to get user");
  }

  return json.data;
}

export function logout() {
  localStorage.removeItem("access_token");
}

export function getAuthToken(): string | null {
  return localStorage.getItem("access_token");
}
