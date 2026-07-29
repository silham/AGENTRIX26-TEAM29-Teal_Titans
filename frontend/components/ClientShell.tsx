"use client";

import { useEffect } from "react";
import { LanguageProvider } from "@/lib/i18n";
import BottomNav from "./BottomNav";

/**
 * The app's single client boundary. It wraps `children` (rather than sitting
 * beside them) so the language context is available to every page — the root
 * layout stays a server component, which keeps `metadata` working.
 */
export default function ClientShell({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Registered here, not in InstallPrompt: that component lives in Navbar,
    // which /auth does not render. Registration has to happen on every route,
    // because without a worker Chrome never offers installation at all.
    //
    // Production only — in dev a worker caches bundles that HMR then replaces,
    // which shows up as stale pages that survive a refresh.
    if (process.env.NODE_ENV !== "production") return;
    if (!("serviceWorker" in navigator)) return;

    navigator.serviceWorker.register("/sw.js").catch(() => {
      // A worker that fails to register costs installability and the offline
      // page. Everything else keeps working, so this stays silent.
    });
  }, []);

  return (
    <LanguageProvider>
      {children}
      <BottomNav />
    </LanguageProvider>
  );
}
