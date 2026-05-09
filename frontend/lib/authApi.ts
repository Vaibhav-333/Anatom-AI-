/**
 * authApi.ts — Typed API client for all auth and user endpoints.
 *
 * Automatically attaches the Bearer token from the auth store, and attempts a
 * silent token refresh when a 401 is received before retrying.
 */

import { useAuthStore } from "@/lib/authStore";

// In production (Vercel), NEXT_PUBLIC_API_URL is often not set.
// Fall back to "/api" so every call is routed through the Next.js proxy
// at app/api/[...path]/route.ts, which reads the server-side API_URL env var
// at request time — no rebuild needed when the backend URL changes.
const BASE =
  process.env.NEXT_PUBLIC_API_URL && process.env.NEXT_PUBLIC_API_URL !== "http://localhost:8000"
    ? process.env.NEXT_PUBLIC_API_URL
    : "/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface SignupPayload {
  username: string;
  password: string;
}

export interface SignupResult {
  user_id: string;
  username: string;
  message: string;
}

export interface SendOtpPayload {
  user_id: string;
  contact_type: "email" | "phone";
  contact_value: string;
  purpose: "signup" | "reset_password";
}

export interface SendOtpResult {
  message: string;
  masked_contact: string;
  dev_otp?: string;
}

export interface VerifyOtpPayload {
  user_id: string;
  otp: string;
  purpose: string;
  contact_type: string;
}

export interface LoginPayload {
  username: string;
  password: string;
  remember_me?: boolean;
  device_info?: string;
}

export interface TokenResult {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user_id: string;
  username: string;
  health_profile_done: boolean;
  expires_in: number;
}

export interface ForgotPasswordPayload {
  identifier: string;
}

export interface ForgotPasswordResult {
  user_id: string;
  message: string;
  masked_contact: string;
  contact_type: string;
  dev_otp?: string;
}

export interface ResetPasswordPayload {
  user_id: string;
  otp: string;
  new_password: string;
}

export interface UserResult {
  id: string;
  username: string;
  email?: string | null;
  phone?: string | null;
  email_verified: boolean;
  phone_verified: boolean;
  health_profile_done: boolean;
  last_login?: string | null;
  created_at: string;
}

export interface HealthProfilePayload {
  age: number;
  gender: string;
  height_cm: number;
  weight_kg: number;
  blood_group: string;
  conditions: string[];
  allergies: string[];
  smoking: boolean;
  alcohol: string;
  activity_level: string;
  family_history: string[];
}

// ---------------------------------------------------------------------------
// Internal fetch wrapper
// ---------------------------------------------------------------------------

async function request<T>(
  path: string,
  options: RequestInit = {},
  withAuth = false,
  _retried = false
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };

  if (withAuth) {
    const token = useAuthStore.getState().accessToken;
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  // Silent refresh on 401
  if (res.status === 401 && withAuth && !_retried) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      const newToken = useAuthStore.getState().accessToken;
      headers["Authorization"] = `Bearer ${newToken}`;
      const retry = await fetch(`${BASE}${path}`, { ...options, headers });
      if (!retry.ok) throw new ApiError(retry.status, await retry.text());
      return retry.json() as Promise<T>;
    }
    useAuthStore.getState().logout();
    throw new ApiError(401, "Session expired. Please log in again.");
  }

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (Array.isArray(body.detail)) {
        // FastAPI/Pydantic validation errors — extract human-readable messages
        detail = body.detail
          .map((e: { msg: string }) => e.msg.replace(/^Value error,\s*/i, ""))
          .join(". ");
      } else if (typeof body.detail === "string") {
        detail = body.detail;
      } else {
        detail = JSON.stringify(body);
      }
    } catch {
      detail = await res.text();
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as unknown as T;
  return res.json() as Promise<T>;
}

async function tryRefresh(): Promise<boolean> {
  const { refreshToken, setTokens } = useAuthStore.getState();
  if (!refreshToken) return false;
  try {
    const res = await fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;
    const data: TokenResult = await res.json();
    setTokens(data.access_token, data.refresh_token, data.expires_in);
    return true;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Public error class
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ---------------------------------------------------------------------------
// Auth API calls
// ---------------------------------------------------------------------------

export const authApi = {
  signup: (body: SignupPayload) =>
    request<SignupResult>("/auth/signup", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  checkUsername: (username: string) =>
    request<{ username: string; available: boolean }>(
      `/auth/check-username?username=${encodeURIComponent(username)}`
    ),

  sendOtp: (body: SendOtpPayload) =>
    request<SendOtpResult>("/auth/send-otp", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  verifyOtp: (body: VerifyOtpPayload) =>
    request<{ verified: boolean; message: string }>("/auth/verify-otp", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  login: (body: LoginPayload) =>
    request<TokenResult>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  logout: (refreshToken: string) =>
    request<void>("/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    }),

  forgotPassword: (body: ForgotPasswordPayload) =>
    request<ForgotPasswordResult>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  resetPassword: (body: ResetPasswordPayload) =>
    request<{ message: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getMe: () => request<UserResult>("/user/me", {}, true),

  saveHealthProfile: (body: HealthProfilePayload) =>
    request<unknown>("/user/health-profile", {
      method: "POST",
      body: JSON.stringify(body),
    }, true),

  getHealthProfile: () =>
    request<unknown>("/user/health-profile", {}, true),
};
