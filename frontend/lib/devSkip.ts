/**
 * devSkip.ts — DEV BYPASS: skip auth and go straight to the dashboard.
 * Remove this file and all imports before production.
 */

import { useAuthStore } from "@/lib/authStore";

export function devSkip(router: { replace: (path: string) => void }) {
  const { setTokens, setUser } = useAuthStore.getState();

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
