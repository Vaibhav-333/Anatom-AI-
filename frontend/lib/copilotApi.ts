/**
 * copilotApi.ts — API client for the AI Health Copilot.
 *
 * Token strategy:
 *  1. Try useAuthStore.getState() (works when Zustand is hydrated)
 *  2. Fall back to reading localStorage directly (works before hydration)
 *  3. On 401, silently refresh via refresh token, then retry once
 *  4. Never call logout() — user is still authenticated via cookie
 */

import { useAuthStore } from "@/lib/authStore";
import { CopilotConversation, CopilotMessage } from "@/lib/copilotStore";

// Use the /api proxy (Next.js rewrites → backend) so browser requests are
// same-origin — avoids CORS issues in production and works locally too.
const BASE = "/api";
const STORAGE_KEY = "anatom-auth"; // must match authStore persist name

// ── Token helpers ─────────────────────────────────────────────────────────────

function _readStorage() {
  try {
    const raw = typeof localStorage !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
    if (!raw) return null;
    return JSON.parse(raw)?.state ?? null;
  } catch {
    return null;
  }
}

/** Read the access token from store OR localStorage (handles pre-hydration). */
function currentToken(): string | null {
  const t = useAuthStore.getState().accessToken;
  if (t) return t;
  return _readStorage()?.accessToken ?? null;
}

function currentRefreshToken(): string | null {
  const t = useAuthStore.getState().refreshToken;
  if (t) return t;
  return _readStorage()?.refreshToken ?? null;
}

function currentExpiresAt(): number | null {
  const t = useAuthStore.getState().expiresAt;
  if (t) return t;
  return _readStorage()?.expiresAt ?? null;
}

/** True when the stored access token is missing or expires within 60 seconds. */
function isTokenExpiredOrStale(): boolean {
  if (!currentToken()) return true;
  const expiresAt = currentExpiresAt();
  if (!expiresAt) return false; // unknown — let the request try
  return Date.now() >= expiresAt - 60_000;
}

async function tryRefresh(): Promise<boolean> {
  const refreshToken = currentRefreshToken();
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${BASE}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    useAuthStore.getState().setTokens(data.access_token, data.refresh_token, data.expires_in);
    return true;
  } catch {
    return false;
  }
}

/** Ensure the access token is fresh before making a request. */
async function ensureFreshToken(): Promise<void> {
  if (isTokenExpiredOrStale()) {
    await tryRefresh();
  }
}

/** True when the user has a valid (or refreshable) session. */
export async function checkAuth(): Promise<boolean> {
  if (currentToken() && !isTokenExpiredOrStale()) return true;
  return tryRefresh();
}

function authHeader(token: string | null): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── SSE Chat stream ───────────────────────────────────────────────────────────

export interface StreamCallbacks {
  onInit: (conversationId: string) => void;
  onToken: (token: string) => void;
  onSuggested: (questions: string[]) => void;
  onDone: () => void;
  onError: (msg: string) => void;
}

async function doFetchStream(token: string | null, body: object, signal?: AbortSignal) {
  return fetch(`${BASE}/copilot/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader(token) },
    body: JSON.stringify(body),
    signal,
  });
}

export async function streamCopilotChat(
  params: {
    query: string;
    conversationId?: string | null;
    reportId?: string | null;
    contextPage?: string;
  },
  callbacks: StreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const body = {
    query: params.query,
    conversation_id: params.conversationId ?? null,
    report_id: params.reportId ?? null,
    context_page: params.contextPage ?? "dashboard",
  };

  await ensureFreshToken();
  let token = currentToken();
  let res: Response;

  try {
    res = await doFetchStream(token, body, signal);
  } catch (err: any) {
    if (err?.name !== "AbortError")
      callbacks.onError("Network error — make sure the server is running.");
    return;
  }

  // On 401: refresh token silently, then retry once
  if (res.status === 401) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      token = currentToken();
      try {
        res = await doFetchStream(token, body, signal);
      } catch (err: any) {
        if (err?.name !== "AbortError")
          callbacks.onError("Network error after token refresh.");
        return;
      }
    }
  }

  // Still failing after refresh attempt
  if (!res.ok) {
    let detail = "";
    try {
      const j = await res.json();
      detail = j.detail ?? JSON.stringify(j);
    } catch {
      detail = await res.text().catch(() => res.statusText);
    }

    if (res.status === 401 || res.status === 403) {
      callbacks.onError(
        "Authentication failed. Please refresh the page and try again."
      );
    } else {
      callbacks.onError(`Server error (${res.status}): ${detail}`);
    }
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    callbacks.onError("No response body from server.");
    return;
  }

  await consumeSSE(reader, callbacks);
}

async function consumeSSE(
  reader: ReadableStreamDefaultReader<Uint8Array>,
  callbacks: StreamCallbacks
) {
  const decoder = new TextDecoder();
  let buffer = "";
  // Guard so onDone is called exactly once — either from the SSE "done"
  // event OR when the stream closes naturally without sending that event.
  let doneCalled = false;

  const callDone = () => {
    if (!doneCalled) {
      doneCalled = true;
      callbacks.onDone();
    }
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";

      for (const part of parts) {
        const trimmed = part.trim();
        if (!trimmed.startsWith("data:")) continue;
        const jsonStr = trimmed.slice(5).trim();
        if (!jsonStr) continue;

        try {
          const payload = JSON.parse(jsonStr);
          switch (payload.type) {
            case "init":      callbacks.onInit(payload.conversation_id); break;
            case "token":     callbacks.onToken(payload.content ?? ""); break;
            case "suggested": callbacks.onSuggested(payload.questions ?? []); break;
            case "done":      callDone(); break;
            case "error":     callbacks.onError(payload.message ?? "Unknown AI error."); break;
          }
        } catch { /* skip malformed SSE chunk */ }
      }
    }
    // Stream closed naturally (done === true from reader) — if the backend
    // never sent a {"type":"done"} event, finalise here so the typing
    // indicator doesn't spin forever.
    callDone();
  } catch (err: any) {
    if (err?.name !== "AbortError")
      callbacks.onError(err?.message ?? "Stream read error.");
    else
      callDone(); // AbortError means user navigated away — still finalise
  }
}

// ── REST helpers (all with token + retry) ─────────────────────────────────────

async function authedFetch(url: string, options: RequestInit = {}): Promise<Response> {
  await ensureFreshToken();
  let token = currentToken();
  let res = await fetch(url, {
    ...options,
    headers: { ...authHeader(token), ...(options.headers as object ?? {}) },
  });

  if (res.status === 401) {
    const refreshed = await tryRefresh();
    if (refreshed) {
      token = currentToken();
      res = await fetch(url, {
        ...options,
        headers: { ...authHeader(token), ...(options.headers as object ?? {}) },
      });
    }
  }

  return res;
}

export async function fetchConversations(): Promise<CopilotConversation[]> {
  if (!currentToken()) return [];
  try {
    const res = await authedFetch(`${BASE}/copilot/conversations`);
    if (!res.ok) return [];
    return res.json();
  } catch { return []; }
}

export async function fetchHistory(conversationId: string): Promise<CopilotMessage[]> {
  try {
    const res = await authedFetch(`${BASE}/copilot/history/${conversationId}`);
    if (!res.ok) return [];
    const data = await res.json();
    return (data.messages ?? []).map((m: any) => ({
      id: m.id, role: m.role, content: m.content, createdAt: m.created_at,
    }));
  } catch { return []; }
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await authedFetch(`${BASE}/copilot/history/${conversationId}`, { method: "DELETE" });
}

export async function fetchSuggestedQuestions(reportId: string): Promise<string[]> {
  try {
    const res = await authedFetch(`${BASE}/copilot/suggested/${reportId}`);
    if (!res.ok) return [];
    const data = await res.json();
    return data.questions ?? [];
  } catch { return []; }
}

export async function embedReport(reportId: string): Promise<void> {
  try {
    await authedFetch(`${BASE}/copilot/embed/${reportId}`, { method: "POST" });
  } catch { /* non-critical */ }
}
