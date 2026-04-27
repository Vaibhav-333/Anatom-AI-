/**
 * (auth)/layout.tsx — minimal layout for all auth pages.
 * The root layout's ClientShell already hides the Sidebar/TopBar on these
 * routes, so this file exists only to satisfy Next.js route grouping.
 */

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
