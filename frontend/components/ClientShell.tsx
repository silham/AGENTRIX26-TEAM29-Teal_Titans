"use client";

import { LanguageProvider } from "@/lib/i18n";
import BottomNav from "./BottomNav";

/**
 * The app's single client boundary. It wraps `children` (rather than sitting
 * beside them) so the language context is available to every page — the root
 * layout stays a server component, which keeps `metadata` working.
 */
export default function ClientShell({ children }: { children: React.ReactNode }) {
  return (
    <LanguageProvider>
      {children}
      <BottomNav />
    </LanguageProvider>
  );
}
