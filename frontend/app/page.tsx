"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  CreditCard, FileSearch, Car, FileText, Store, Flame,
  MessageSquarePlus, ClipboardList, HelpCircle,
  ChevronRight, ArrowRight,
} from "lucide-react";
import Navbar from "@/components/Navbar";

const QUICK_ACTIONS = [
  { Icon: MessageSquarePlus, label: "Get Help",  href: "/goal",      bg: "bg-blue-100",   color: "text-blue-700"   },
  { Icon: ClipboardList,     label: "My Plans",  href: "/dashboard", bg: "bg-purple-100", color: "text-purple-700" },
  { Icon: HelpCircle,        label: "How?",      href: "#how",       bg: "bg-teal-100",   color: "text-teal-700"   },
];

const SERVICES = [
  {
    Icon: CreditCard, label: "Lost my ID card",
    sub: "Get a replacement NIC",
    href: "/goal?q=I+lost+my+NIC+and+need+a+replacement",
    bg: "bg-red-100", color: "text-red-600",
  },
  {
    Icon: FileSearch, label: "Need a passport",
    sub: "Apply or renew your passport",
    href: "/goal?q=I+want+to+apply+for+a+passport",
    bg: "bg-violet-100", color: "text-violet-600",
  },
  {
    Icon: Car, label: "Driving licence",
    sub: "Renew or apply for the first time",
    href: "/goal?q=I+want+to+renew+my+driving+licence",
    bg: "bg-sky-100", color: "text-sky-600",
  },
  {
    Icon: FileText, label: "Birth certificate",
    sub: "Get a certified copy",
    href: "/goal?q=I+need+a+copy+of+my+birth+certificate",
    bg: "bg-teal-100", color: "text-teal-600",
  },
  {
    Icon: Store, label: "Start a business",
    sub: "Registration and licence steps",
    href: "/goal?q=I+am+starting+a+small+business",
    bg: "bg-green-100", color: "text-green-600",
  },
  {
    Icon: Flame, label: "Lost all documents",
    sub: "After flood, fire or theft",
    href: "/goal?q=I+lost+all+my+documents+in+a+flood",
    bg: "bg-orange-100", color: "text-orange-600",
  },
];

export default function LandingPage() {
  return (
    <div className="flex min-h-dvh flex-col bg-(--background)">
      <Navbar />

      <main className="flex-1 px-4 pb-8 pt-5">
        <div className="mx-auto max-w-lg space-y-5">

          {/* ── Greeting ──────────────────────────────────────── */}
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <p className="text-sm text-(--muted-fg)">Welcome to</p>
            <h1 className="text-2xl font-extrabold text-(--foreground)">HelpLK</h1>
            <p className="text-sm text-(--muted-fg)">Your Sri Lanka government services guide</p>
          </motion.div>

          {/* ── Quick actions ────────────────────────────────── */}
          <div className="grid grid-cols-3 gap-3">
            {QUICK_ACTIONS.map(({ Icon, label, href, bg, color }, i) => (
              <motion.div
                key={label}
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
                  <span className="text-xs font-semibold text-(--foreground)">{label}</span>
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
                Start Here
              </p>
              <h2 className="mt-1 text-xl font-extrabold leading-snug text-white">
                Tell us what you need help with
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-blue-100">
                Describe your situation in your own words. We find the correct government steps for you.
              </p>
              <div className="mt-4 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-2.5 text-sm font-bold text-(--primary)">
                Get Help Now <ArrowRight size={16} />
              </div>
            </Link>
          </motion.div>

          {/* ── Common services list ─────────────────────────── */}
          <div>
            <h2 className="mb-3 text-base font-bold text-(--foreground)">Common Services</h2>
            <div className="overflow-hidden rounded-2xl bg-white shadow-sm">
              {SERVICES.map(({ Icon, label, sub, href, bg, color }, i) => (
                <motion.div
                  key={label}
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
                      <p className="text-sm font-semibold text-(--foreground)">{label}</p>
                      <p className="text-xs text-(--muted-fg)">{sub}</p>
                    </div>
                    <ChevronRight size={16} className="shrink-0 text-(--muted-fg)" />
                  </Link>
                </motion.div>
              ))}
            </div>
          </div>

          {/* ── How it works ─────────────────────────────────── */}
          <div id="how">
            <h2 className="mb-3 text-base font-bold text-(--foreground)">How it works</h2>
            <div className="space-y-2.5">
              {[
                { n: "1", title: "Tell us what you need", desc: "Describe your situation in your own words — no form names or office addresses needed." },
                { n: "2", title: "We find the steps", desc: "Official government rules are checked and a plan is built just for you." },
                { n: "3", title: "Follow your guide", desc: "A clear list of steps and documents to complete, one at a time." },
              ].map((s, i) => (
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
                    <p className="text-sm font-semibold text-(--foreground)">{s.title}</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-(--muted-fg)">{s.desc}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>

          {/* ── Trust note ───────────────────────────────────── */}
          <div className="rounded-2xl bg-white px-4 py-3.5 shadow-sm">
            <p className="text-sm font-semibold text-(--foreground)">Free and simple to use</p>
            <p className="mt-0.5 text-xs leading-relaxed text-(--muted-fg)">
              Information comes from official Sri Lanka government sources. No registration needed to get started.
            </p>
          </div>

        </div>
      </main>

      <footer className="border-t border-(--border) bg-white px-4 py-5 text-center">
        <p className="text-xs text-(--muted-fg)">HelpLK · Sri Lanka Government Services Guide · 2026</p>
      </footer>
    </div>
  );
}
