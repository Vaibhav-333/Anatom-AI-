/**
 * DEV ONLY — bypass authentication for UI development.
 * Remove this file and all usages before production.
 */

import { useAuthStore } from "@/lib/authStore";

export function devSkip(router: { replace: (path: string) => void }) {
  const { setTokens, setUser } = useAuthStore.getState();

  // Fake token + cookie so middleware passes through
  setTokens("dev-skip-token", "dev-skip-refresh", 86400);
  setUser({
    id: "dev-user",
    username: "dev_user",
    email: "dev@anatom.ai",
    phone: null,
    emailVerified: true,
    phoneVerified: false,
    healthProfileDone: true,
  });

  router.replace("/");
}
