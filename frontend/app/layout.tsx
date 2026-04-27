import type { Metadata, Viewport } from "next";
import "./globals.css";
import "leaflet/dist/leaflet.css";
import { AnimatedGrid } from "@/components/layout/AnimatedGrid";
import { ClientShell } from "@/components/layout/ClientShell";
import { ThemeProvider } from "@/context/ThemeContext";

export const metadata: Metadata = {
  title: "Anatom-AI — Medical Intelligence Platform",
  description:
    "Understand your medical reports, visualize your body in 3D, and get personalized health guidance.",
  icons: { icon: "/favicon.ico" },
};

export const viewport: Viewport = {
  themeColor: "#000000",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body
        className="antialiased bg-navy text-slate-200"
        style={{ backgroundColor: "#000000", color: "#FFFFFF", minHeight: "100vh" }}
      >
        <AnimatedGrid />
        <ThemeProvider>
          <ClientShell>{children}</ClientShell>
        </ThemeProvider>
      </body>
    </html>
  );
}
