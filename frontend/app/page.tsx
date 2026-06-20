"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight, Bot, GitBranch, Shield, FileCheck,
  Clock, Globe, ChevronRight, Zap, Lock
} from "lucide-react";
import Navbar from "@/components/Navbar";
import { DEMO_GOALS } from "@/lib/types";

const FEATURES = [
  { icon: Bot,       title: "Multi-Agent Planning",     desc: "8 specialised agents — Planner, Knowledge, Dependency, Eligibility, Checklist, Document, Form, Reminder — collaborate to manage your procedure." },
  { icon: GitBranch, title: "Dependency-Aware Workflow", desc: "Cannot apply for a passport without a NIC? The Dependency Agent locks blocked steps and tells you exactly what to do first." },
  { icon: Shield,    title: "RAG-Verified Information",  desc: "Every recommendation is backed by official government sources. Verified facts are always separated from AI suggestions with citations." },
  { icon: FileCheck, title: "Smart Document Validation", desc: "Upload your documents and the AI checks for missing signatures, incorrect photos, incomplete fields, and readability issues." },
  { icon: Clock,     title: "Stateful Case Memory",      desc: "Start today, continue next week. Your progress is saved and resumable. The system remembers exactly where you left off." },
  { icon: Globe,     title: "Trilingual Support",        desc: "Available in Sinhala, Tamil, and English. Designed for every Sri Lankan citizen, including those in rural and underserved areas." },
];

const HOW_IT_WORKS = [
  { step: "01", title: "Describe your need",    desc: "Type your goal in plain language. No need to know form names or department codes." },
  { step: "02", title: "Agents plan for you",   desc: "8 AI agents retrieve verified information, check dependencies, and build your personalised workflow." },
  { step: "03", title: "Follow your roadmap",   desc: "Complete tasks in order, upload documents for AI validation, and track progress on your dashboard." },
];

export default function LandingPage() {
  return (
    <div className="flex min-h-dvh flex-col bg-[--background]">
      <Navbar />

      {/* ── Hero ──────────────────────────────────────────────────────── */}
      <section className="relative flex flex-col items-center justify-center overflow-hidden px-4 py-24 text-center sm:py-32 grid-bg">
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="h-[600px] w-[600px] rounded-full bg-[--primary]/8 blur-3xl" />
        </div>

        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6 }}
          className="relative z-10 max-w-4xl"
        >
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[--primary]/30 bg-teal-950/40 px-4 py-1.5 text-sm text-[--primary]">
            <Zap size={13} />
            Agentic AI · RAG · Citizen Services
          </div>

          <h1 className="text-4xl font-extrabold leading-tight text-[--foreground] sm:text-5xl lg:text-6xl">
            Government procedures,{" "}
            <span className="gradient-text">guided step by step</span>
          </h1>

          <p className="mt-6 mx-auto max-w-2xl text-base text-[--muted-fg] sm:text-lg leading-relaxed">
            HelpLK AI is Sri Lanka&apos;s agentic citizen services copilot. Describe your goal
            in plain language and let 8 specialised AI agents plan, verify, and manage the full
            procedure for you — from confusion to completion.
          </p>

          <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <Link
              href="/goal"
              className="flex items-center gap-2 rounded-xl bg-[--primary] px-7 py-3.5 text-base font-semibold text-white shadow-lg hover:bg-teal-500 transition-colors glow-teal"
            >
              Start My Procedure
              <ArrowRight size={18} />
            </Link>
            <Link
              href="/dashboard"
              className="flex items-center gap-2 rounded-xl border border-[--border] px-7 py-3.5 text-base text-[--foreground] hover:border-[--primary]/60 hover:bg-teal-950/20 transition-colors"
            >
              View Dashboard
            </Link>
          </div>
        </motion.div>

        <motion.div
          initial={{ y: 20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.35, duration: 0.6 }}
          className="relative z-10 mt-12 flex max-w-3xl flex-wrap justify-center gap-2"
        >
          {DEMO_GOALS.map((goal) => (
            <Link
              key={goal}
              href={`/goal?q=${encodeURIComponent(goal)}`}
              className="group flex items-center gap-1.5 rounded-full border border-[--border] bg-[--surface] px-3.5 py-1.5 text-xs text-[--muted-fg] hover:border-[--primary]/50 hover:text-[--primary] transition-colors"
            >
              {goal}
              <ChevronRight size={11} className="opacity-0 group-hover:opacity-100 transition-opacity" />
            </Link>
          ))}
        </motion.div>
      </section>

      {/* ── vs ChatGPT ──────────────────────────────────────────────── */}
      <section className="border-y border-[--border] bg-[--surface] px-4 py-10">
        <div className="mx-auto max-w-4xl">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-[--border] p-5">
              <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-[--muted-fg]">Generic AI (ChatGPT / Gemini)</p>
              <ul className="space-y-2 text-sm text-[--muted-fg]">
                {["Stateless Q&A conversations","May hallucinate procedures","No dependency tracking","No document validation","No progress memory"].map(x => (
                  <li key={x} className="flex items-center gap-2"><span className="text-[--danger]">✕</span> {x}</li>
                ))}
              </ul>
            </div>
            <div className="rounded-xl border border-[--primary]/50 bg-teal-950/20 p-5 glow-teal">
              <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-[--primary]">HelpLK AI</p>
              <ul className="space-y-2 text-sm text-[--foreground]">
                {["Stateful citizen case management","RAG from official government sources","Dependency-aware step locking","AI document verification","Resume progress anytime"].map(x => (
                  <li key={x} className="flex items-center gap-2"><span className="text-[--success]">✓</span> {x}</li>
                ))}
              </ul>
            </div>
          </div>
          <p className="mt-5 text-center text-sm text-[--muted-fg]">
            <span className="gradient-text font-semibold">ChatGPT answers questions.</span>{" "}
            HelpLK AI manages the citizen journey.
          </p>
        </div>
      </section>

      {/* ── How it works ────────────────────────────────────────────── */}
      <section className="px-4 py-20">
        <div className="mx-auto max-w-5xl">
          <div className="mb-12 text-center">
            <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-[--primary]">How it works</p>
            <h2 className="text-3xl font-bold text-[--foreground]">From confusion to completion</h2>
          </div>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
            {HOW_IT_WORKS.map((item, i) => (
              <motion.div
                key={item.step}
                initial={{ y: 16, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="relative rounded-2xl border border-[--border] bg-[--surface] p-6"
              >
                <span className="gradient-text-gold text-4xl font-extrabold">{item.step}</span>
                <h3 className="mt-3 font-semibold text-[--foreground]">{item.title}</h3>
                <p className="mt-2 text-sm text-[--muted-fg] leading-relaxed">{item.desc}</p>
                {i < 2 && <ChevronRight size={20} className="absolute -right-3 top-1/2 hidden -translate-y-1/2 text-[--border] sm:block" />}
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features grid ───────────────────────────────────────────── */}
      <section className="bg-[--surface] px-4 py-20">
        <div className="mx-auto max-w-6xl">
          <div className="mb-12 text-center">
            <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-[--primary]">Features</p>
            <h2 className="text-3xl font-bold text-[--foreground]">Everything a citizen needs</h2>
          </div>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ y: 16, opacity: 0 }}
                whileInView={{ y: 0, opacity: 1 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.06 }}
                className="group rounded-2xl border border-[--border] bg-[--background] p-6 hover:border-[--primary]/40 transition-colors"
              >
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl bg-teal-950/50 border border-[--primary]/20 group-hover:bg-teal-950/80 transition-colors">
                  <f.icon size={20} className="text-[--primary]" />
                </div>
                <h3 className="font-semibold text-[--foreground]">{f.title}</h3>
                <p className="mt-2 text-sm text-[--muted-fg] leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Agent flow ──────────────────────────────────────────────── */}
      <section className="px-4 py-20">
        <div className="mx-auto max-w-5xl">
          <div className="mb-10 text-center">
            <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-[--primary]">Architecture</p>
            <h2 className="text-3xl font-bold text-[--foreground]">8 agents. One goal.</h2>
          </div>
          <div className="overflow-x-auto pb-4">
            <div className="flex min-w-[640px] flex-wrap items-center justify-center gap-2">
              {["Planner","Knowledge","Dependency","Eligibility","Checklist","Document","Form","Reminder"].map((a, i) => (
                <motion.div key={a} initial={{ scale: 0.8, opacity: 0 }} whileInView={{ scale: 1, opacity: 1 }} viewport={{ once: true }} transition={{ delay: i * 0.07, type: "spring" }} className="flex items-center gap-2">
                  <div className="rounded-xl border border-[--primary]/40 bg-teal-950/30 px-4 py-3 text-center">
                    <p className="text-xs font-semibold text-[--primary]">{a}</p>
                    <p className="text-[10px] text-[--muted-fg]">Agent</p>
                  </div>
                  {i < 7 && <ChevronRight size={14} className="text-[--border] shrink-0" />}
                </motion.div>
              ))}
            </div>
          </div>
          <p className="mt-6 text-center text-sm text-[--muted-fg]">
            Powered by <span className="text-[--foreground]">LangGraph</span> ·{" "}
            <span className="text-[--foreground]">Groq Llama 3.3 70B</span> ·{" "}
            <span className="text-[--foreground]">Gemini 1.5 Flash</span> ·{" "}
            <span className="text-[--foreground]">LlamaIndex</span>
          </p>
        </div>
      </section>

      {/* ── CTA ─────────────────────────────────────────────────────── */}
      <section className="px-4 py-20 bg-[--surface]">
        <motion.div
          initial={{ y: 16, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          className="mx-auto max-w-2xl rounded-3xl border border-[--primary]/40 bg-gradient-to-b from-teal-950/40 to-[--surface] p-10 text-center glow-teal"
        >
          <Lock size={32} className="mx-auto mb-4 text-[--primary]" />
          <h2 className="text-2xl font-bold text-[--foreground] sm:text-3xl">Stop guessing. Start completing.</h2>
          <p className="mt-4 text-[--muted-fg]">Describe your government service need and let HelpLK AI manage the entire journey.</p>
          <Link href="/goal" className="mt-8 inline-flex items-center gap-2 rounded-xl bg-[--primary] px-8 py-3.5 text-base font-semibold text-white hover:bg-teal-500 transition-colors">
            Start My Procedure <ArrowRight size={18} />
          </Link>
        </motion.div>
      </section>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer className="border-t border-[--border] px-4 py-8 text-center">
        <p className="text-sm text-[--muted-fg]">HelpLK AI · Built for Sri Lanka · AGENTRIX Hackathon 2026</p>
        <p className="mt-1 text-xs text-[--muted-fg]/60">LangGraph · Groq · Gemini · LlamaIndex · FastAPI · Next.js 16</p>
      </footer>
    </div>
  );
}
