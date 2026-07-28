"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Eye, EyeOff, Loader2, LogIn, UserPlus } from "lucide-react";
import Link from "next/link";
import { signIn } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { cn } from "@/lib/cn";

type Mode = "signin" | "signup";

function AuthContent() {
  const router     = useRouter();
  const params     = useSearchParams();
  const t          = useT();

  const emailRef = useRef<HTMLInputElement>(null);

  const [mode,      setMode]      = useState<Mode>("signin");
  const [email,     setEmail]     = useState("");
  const [name,      setName]      = useState("");
  const [password,  setPassword]  = useState("");
  const [showPwd,   setShowPwd]   = useState(false);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState("");
  const [pendingGoal, setPendingGoal] = useState<string | null>(null);

  // Read the pending goal saved before the auth redirect
  useEffect(() => {
    const saved = sessionStorage.getItem("helplk_pending_goal");
    if (saved) setPendingGoal(saved);
    emailRef.current?.focus();
  }, []);

  function redirectAfterAuth() {
    const next = params.get("next") ?? "/goal";
    router.replace(next);
  }

  async function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    if (!email.trim()) { setError(t("auth.errNoEmail")); return; }
    if (mode === "signup" && !name.trim()) { setError(t("auth.errNoName")); return; }

    setLoading(true);
    setError("");
    try {
      await signIn(email.trim(), mode === "signup" ? name.trim() : undefined);
      redirectAfterAuth();
    } catch {
      setError(t("auth.errSignIn"));
      setLoading(false);
    }
  }

  async function handleDemo() {
    setLoading(true);
    setError("");
    try {
      // Mint a demo token via the legacy demo-token route
      const res  = await fetch("/api/demo-token", { method: "POST" });
      const data = await res.json() as { token: string };
      sessionStorage.setItem("helplk_token", data.token);
      sessionStorage.setItem(
        "helplk_user",
        JSON.stringify({ email: "demo@helplk.ai", name: "Demo User" }),
      );
      redirectAfterAuth();
    } catch {
      setError(t("auth.errDemo"));
      setLoading(false);
    }
  }

  const isSignup = mode === "signup";

  return (
    <div className="flex min-h-dvh flex-col bg-(--background)">

      {/* Minimal top bar */}
      <header className="w-full border-b border-(--border) bg-white px-4 py-3">
        <div className="mx-auto flex max-w-lg items-center gap-2.5">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-(--primary)">
              <span className="text-xs font-bold text-white">LK</span>
            </div>
            <span className="text-base font-bold text-(--foreground)">{t("nav.brand")}</span>
          </Link>
        </div>
      </header>

      <main className="flex flex-1 items-start justify-center px-4 pb-12 pt-10">
        <div className="w-full max-w-sm">

          {/* Pending goal banner */}
          <AnimatePresence>
            {pendingGoal && (
              <motion.div
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="mb-6 rounded-2xl border border-blue-200 bg-blue-50 px-4 py-3.5"
              >
                <p className="text-xs font-semibold uppercase tracking-wide text-blue-500 mb-1">
                  {t("auth.yourRequest")}
                </p>
                <p className="text-sm font-medium leading-snug text-(--foreground) line-clamp-2">
                  &ldquo;{pendingGoal}&rdquo;
                </p>
                <p className="mt-1.5 text-xs text-blue-500">
                  {t("auth.signInToSave")}
                </p>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Heading */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6"
          >
            <h1 className="text-2xl font-extrabold text-(--foreground)">
              {isSignup ? t("auth.headingSignup") : t("auth.headingSignin")}
            </h1>
            <p className="mt-1 text-sm text-(--muted-fg)">
              {isSignup ? t("auth.subSignup") : t("auth.subSignin")}
            </p>
          </motion.div>

          {/* Mode toggle */}
          <div className="mb-5 grid grid-cols-2 gap-1 rounded-2xl border border-(--border) bg-white p-1 shadow-sm">
            {(["signin", "signup"] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setError(""); }}
                className={cn(
                  "flex items-center justify-center gap-2 rounded-xl py-2.5 text-sm font-semibold transition-colors",
                  mode === m
                    ? "bg-(--primary) text-white shadow"
                    : "text-(--muted-fg) hover:text-(--foreground)",
                )}
              >
                {m === "signin" ? <LogIn size={15} /> : <UserPlus size={15} />}
                {m === "signin" ? t("auth.signIn") : t("auth.createAccount")}
              </button>
            ))}
          </div>

          {/* Form */}
          <motion.form
            key={mode}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18 }}
            onSubmit={handleSubmit}
            className="space-y-3"
          >
            {/* Name — signup only */}
            <AnimatePresence>
              {isSignup && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.18 }}
                  className="overflow-hidden"
                >
                  <label className="mb-1.5 block text-sm font-semibold text-(--foreground)">
                    {t("auth.fullName")}
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder={t("auth.fullNamePlaceholder")}
                    autoComplete="name"
                    className="w-full rounded-xl border border-(--border) bg-white px-4 py-3 text-sm text-(--foreground) placeholder:text-(--muted-fg) focus:border-(--primary) focus:outline-none focus:ring-2 focus:ring-(--primary)/20 transition-all"
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Email */}
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-(--foreground)">
                {t("auth.email")}
              </label>
              <input
                ref={emailRef}
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t("auth.emailPlaceholder")}
                autoComplete="email"
                required
                className="w-full rounded-xl border border-(--border) bg-white px-4 py-3 text-sm text-(--foreground) placeholder:text-(--muted-fg) focus:border-(--primary) focus:outline-none focus:ring-2 focus:ring-(--primary)/20 transition-all"
              />
            </div>

            {/* Password */}
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-(--foreground)">
                {t("auth.password")}
              </label>
              <div className="relative">
                <input
                  type={showPwd ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={isSignup ? t("auth.passwordCreate") : t("auth.passwordEnter")}
                  autoComplete={isSignup ? "new-password" : "current-password"}
                  className="w-full rounded-xl border border-(--border) bg-white px-4 py-3 pr-11 text-sm text-(--foreground) placeholder:text-(--muted-fg) focus:border-(--primary) focus:outline-none focus:ring-2 focus:ring-(--primary)/20 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPwd((p) => !p)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-(--muted-fg) hover:text-(--foreground) transition-colors"
                  tabIndex={-1}
                  aria-label={t("auth.togglePassword")}
                >
                  {showPwd ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Error */}
            <AnimatePresence>
              {error && (
                <motion.p
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-(--danger)"
                >
                  {error}
                </motion.p>
              )}
            </AnimatePresence>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !email.trim()}
              className={cn(
                "flex w-full items-center justify-center gap-2 rounded-xl py-3.5 text-sm font-bold transition-all active:scale-95",
                loading || !email.trim()
                  ? "bg-(--border) text-(--muted-fg) cursor-not-allowed"
                  : "bg-(--primary) text-white shadow-sm hover:bg-(--primary-dark)",
              )}
            >
              {loading ? (
                <Loader2 size={17} className="animate-spin" />
              ) : (
                <>
                  {isSignup ? t("auth.createAccount") : t("auth.signIn")}
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </motion.form>

          {/* Divider */}
          <div className="my-5 flex items-center gap-3">
            <div className="h-px flex-1 bg-(--border)" />
            <span className="text-xs font-medium text-(--muted-fg)">{t("auth.or")}</span>
            <div className="h-px flex-1 bg-(--border)" />
          </div>

          {/* Demo mode */}
          <button
            onClick={handleDemo}
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-(--border) bg-white py-3.5 text-sm font-semibold text-(--foreground) transition-all hover:border-(--primary) hover:text-(--primary) active:scale-95 shadow-sm"
          >
            {loading
              ? <Loader2 size={17} className="animate-spin text-(--muted-fg)" />
              : t("auth.demo")}
          </button>

          <p className="mt-4 text-center text-xs leading-relaxed text-(--muted-fg)">
            {t("auth.terms")}
          </p>

        </div>
      </main>
    </div>
  );
}

export default function AuthPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-dvh items-center justify-center bg-(--background)">
          <Loader2 size={32} className="animate-spin text-(--primary)" />
        </div>
      }
    >
      <AuthContent />
    </Suspense>
  );
}
