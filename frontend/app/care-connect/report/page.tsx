"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ReportWizardRedirect() {
  const router = useRouter();
  useEffect(() => { router.replace("/upload"); }, [router]);
  return null;
}
