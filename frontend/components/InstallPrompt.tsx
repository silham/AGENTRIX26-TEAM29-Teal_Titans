"use client";

import { useEffect, useState } from "react";
import { Download } from "lucide-react";
import { useT } from "@/lib/i18n";

/**
 * The "install app" button.
 *
 * Worth having rather than leaving it to the browser: Chrome's own install
 * entry is buried in an overflow menu most citizens will never open, and a
 * home-screen icon is the difference between a site someone visits once and
 * one they return to mid-procedure weeks later.
 *
 * Service worker registration deliberately does NOT live here — it belongs in
 * ClientShell. This component renders inside Navbar, which the auth page does
 * not use, so registering here would skip that route entirely.
 */

// Not in TypeScript's DOM lib: Chromium-only, still non-standard.
interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

export default function InstallPrompt() {
  const t = useT();
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    const onPrompt = (e: Event) => {
      // Suppress Chrome's own mini-infobar so ours is the only affordance.
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
    };
    // Once installed the event never fires again; clear any pending button.
    const onInstalled = () => setDeferred(null);

    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  if (!deferred) return null;

  async function install() {
    if (!deferred) return;
    await deferred.prompt();
    await deferred.userChoice;
    // The prompt is single-use — a second `prompt()` call throws.
    setDeferred(null);
  }

  return (
    <button
      onClick={install}
      title={t("nav.install")}
      aria-label={t("nav.install")}
      className="flex h-9 items-center gap-1.5 rounded-xl border border-(--primary) bg-white px-2.5 text-xs font-semibold text-(--primary) hover:bg-(--primary-light) active:scale-95 transition-all"
    >
      <Download size={14} className="shrink-0" />
      <span className="hidden sm:inline">{t("nav.install")}</span>
    </button>
  );
}
