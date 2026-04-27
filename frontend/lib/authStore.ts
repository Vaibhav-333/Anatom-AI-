/**
 * authStore.ts — Zustand store for authentication state.
 *
 * Persists the JWT pair and user info to localStorage so sessions survive page
 * refreshes.  The access token is stored in memory (via Zustand) and also in a
 * js-accessible cookie so Next.js middleware can read it for route protection.
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AuthUser {
  id: string;
  username: string;
  email?: string | null;
  phone?: string | null;
  emailVerified: boolean;
  phoneVerified: boolean;
  healthProfileDone: boolean;
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  refreshToken: string | null;
  /** Timestamp (ms) when the access token expires */
  expiresAt: number | null;
  isAuthenticated: boolean;

  setTokens: (
    accessToken: string,
    refreshToken: string,
    expiresIn: number
  ) => void;
  setUser: (user: AuthUser) => void;
  updateHealthProfileDone: (done: boolean) => void;
  logout: () => void;
}

// ---------------------------------------------------------------------------
// Cookie helpers (for Next.js middleware)
// ---------------------------------------------------------------------------

function setCookie(name: string, value: string, maxAgeSeconds: number) {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=${encodeURIComponent(value)}; path=/; max-age=${maxAgeSeconds}; SameSite=Lax`;
}

function deleteCookie(name: string) {
  if (typeof document === "undefined") return;
  document.cookie = `${name}=; path=/; max-age=0`;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      expiresAt: null,
      isAuthenticated: false,

      setTokens: (accessToken, refreshToken, expiresIn) => {
        const expiresAt = Date.now() + expiresIn * 1000;
        setCookie("anatom_auth", "1", expiresIn);
        set({ accessToken, refreshToken, expiresAt, isAuthenticated: true });
      },

      setUser: (user) => set({ user }),

      updateHealthProfileDone: (done) =>
        set((state) => ({
          user: state.user ? { ...state.user, healthProfileDone: done } : null,
        })),

      logout: () => {
        deleteCookie("anatom_auth");
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          expiresAt: null,
          isAuthenticated: false,
        });
      },
    }),
    {
      name: "anatom-auth",
      storage: createJSONStorage(() => localStorage),
      // Only persist tokens and user — not function references
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        expiresAt: state.expiresAt,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
