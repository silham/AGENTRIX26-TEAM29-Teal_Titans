"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  CreditCard, FileSearch, Car, FileText, Store, Flame,
  MessageSquarePlus, ClipboardList, HelpCircle,
  ChevronRight, ArrowRight,
} from "lucide-react";
import Navbar from "@/components/Navbar";
import { useT } from "@/lib/i18n";

const QUICK_ACTIONS = [
  { Icon: MessageSquarePlus, key: "landing.quickHelp",  href: "/goal",      bg: "bg-blue-100",   color: "text-blue-700"   },
  { Icon: ClipboardList,     key: "landing.quickPlans", href: "/dashboard", bg: "bg-purple-100", color: "text-purple-700" },
  { Icon: HelpCircle,        key: "landing.quickHow",   href: "#how",       bg: "bg-teal-100",   color: "text-teal-700"   },
];

// The `?q=` goal stays English in every language. It is a stable identifier,
// and the backend's no-LLM fast path recognises these exact phrases — sending
// a translated version would cost a normalisation round trip for no gain.
// Only `labelKey`/`subKey` are translated.
const SERVICES = [
  {
    Icon: CreditCard, labelKey: "landing.svcNicLabel", subKey: "landing.svcNicSub",
    href: "/goal?q=I+lost+my+NIC+and+need+a+replacement",
    bg: "bg-red-100", color: "text-red-600",
  },
  {
    Icon: FileSearch, labelKey: "landing.svcPassportLabel", subKey: "landing.svcPassportSub",
    href: "/goal?q=I+want+to+apply+for+a+passport",
    bg: "bg-violet-100", color: "text-violet-600",
  },
  {
    Icon: Car, labelKey: "landing.svcLicenceLabel", subKey: "landing.svcLicenceSub",
    href: "/goal?q=I+want+to+renew+my+driving+licence",
    bg: "bg-sky-100", color: "text-sky-600",
  },
  {
    Icon: FileText, labelKey: "landing.svcBirthLabel", subKey: "landing.svcBirthSub",
    href: "/goal?q=I+need+a+copy+of+my+birth+certificate",
    bg: "bg-teal-100", color: "text-teal-600",
  },
  {
    Icon: Store, labelKey: "landing.svcBusinessLabel", subKey: "landing.svcBusinessSub",
    href: "/goal?q=I+am+starting+a+small+business",
    bg: "bg-green-100", color: "text-green-600",
  },
  {
    Icon: Flame, labelKey: "landing.svcLostAllLabel", subKey: "landing.svcLostAllSub",
    href: "/goal?q=I+lost+all+my+documents+in+a+flood",
    bg: "bg-orange-100", color: "text-orange-600",
  },
];

const HOW_STEPS = [
  { n: "1", titleKey: "landing.how1Title", descKey: "landing.how1Desc" },
  { n: "2", titleKey: "landing.how2Title", descKey: "landing.how2Desc" },
  { n: "3", titleKey: "landing.how3Title", descKey: "landing.how3Desc" },
];

export default function LandingPage() {
  const t = useT();
  return (
    <div className="flex min-h-dvh flex-col bg-(--background)">
      <Navbar />

      <main className="flex-1 px-4 pb-8 pt-5">
        <div className="mx-auto max-w-lg space-y-5">

          {/* ── Greeting ──────────────────────────────────────── */}
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <p className="text-sm text-(--muted-fg)">{t("landing.welcome")}</p>
            <h1 className="text-2xl font-extrabold text-(--foreground)">{t("nav.brand")}</h1>
            <p className="text-sm text-(--muted-fg)">{t("landing.subtitle")}</p>
          </motion.div>

          {/* ── Quick actions ────────────────────────────────── */}
          <div className="grid grid-cols-3 gap-3">
            {QUICK_ACTIONS.map(({ Icon, key, href, bg, color }, i) => (
              <motion.div
                key={key}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.07 }}
              >
                <Link
                  href={href}
                  className="flex flex-col items-center gap-2 rounded-2xl bg-white p-4 shadow-sm active:scale-95 transition-all"
                >
                  <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${bg} ${color}`}>
                    <Icon size={22} />
                  </div>
                  <span className="text-xs font-semibold text-(--foreground)">{t(key)}</span>
                </Link>
              </motion.div>
            ))}
          </div>

          {/* ── Featured card ────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Link
              href="/goal"
              className="block overflow-hidden rounded-3xl bg-(--primary) p-6 active:scale-[0.98] transition-all"
            >
              <p className="text-xs font-semibold uppercase tracking-wide text-blue-300">
                {t("landing.startHere")}
              </p>
              <h2 className="mt-1 text-xl font-extrabold leading-snug text-white">
                {t("landing.startTitle")}
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-blue-100">
                {t("landing.startBody")}
              </p>
              <div className="mt-4 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-2.5 text-sm font-bold text-(--primary)">
                {t("landing.startCta")} <ArrowRight size={16} />
              </div>
            </Link>
          </motion.div>

          {/* ── Common services list ─────────────────────────── */}
          <div>
            <h2 className="mb-3 text-base font-bold text-(--foreground)">{t("landing.commonServices")}</h2>
            <div className="overflow-hidden rounded-2xl bg-white shadow-sm">
              {SERVICES.map(({ Icon, labelKey, subKey, href, bg, color }, i) => (
                <motion.div
                  key={labelKey}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.1 + i * 0.05 }}
                >
                  <Link
                    href={href}
                    className={`flex items-center gap-4 px-4 py-3.5 active:bg-(--background) transition-colors${
                      i < SERVICES.length - 1 ? " border-b border-(--border)" : ""
                    }`}
                  >
                    <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl ${bg} ${color}`}>
                      <Icon size={20} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-(--foreground)">{t(labelKey)}</p>
                      <p className="text-xs text-(--muted-fg)">{t(subKey)}</p>
                    </div>
                    <ChevronRight size={16} className="shrink-0 text-(--muted-fg)" />
                  </Link>
                </motion.div>
              ))}
            </div>
          </div>

          {/* ── How it works ─────────────────────────────────── */}
          <div id="how">
            <h2 className="mb-3 text-base font-bold text-(--foreground)">{t("landing.howItWorks")}</h2>
            <div className="space-y-2.5">
              {HOW_STEPS.map((s, i) => (
                <motion.div
                  key={s.n}
                  initial={{ opacity: 0, x: -8 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.08 }}
                  className="flex items-start gap-3 rounded-2xl bg-white p-4 shadow-sm"
                >
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-(--primary) text-sm font-extrabold text-white">
                    {s.n}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-(--foreground)">{t(s.titleKey)}</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-(--muted-fg)">{t(s.descKey)}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          {/* ── Trust note ───────────────────────────────────── */}
          <div className="rounded-2xl bg-white px-4 py-3.5 shadow-sm">
            <p className="text-sm font-semibold text-(--foreground)">{t("landing.trustTitle")}</p>
            <p className="mt-0.5 text-xs leading-relaxed text-(--muted-fg)">
              {t("landing.trustBody")}
            </p>
          </div>

        </div>
      </main>

      <footer className="border-t border-(--border) bg-white px-4 py-5 text-center">
        <p className="text-xs text-(--muted-fg)">{t("landing.footer")}</p>
      </footer>
    </div>
  );
}
