"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Loader2, Mic, Square } from "lucide-react";
import { api } from "@/lib/api";
import { useLanguage, useT } from "@/lib/i18n";
import { cn } from "@/lib/cn";
import type { Language } from "@/lib/types";

/**
 * Two transcription paths, so every supported language works on every device:
 *
 * 1. Native Web Speech API (Chrome, Edge, Android) — transcribes client-side,
 *    for free, with no round trip. Used whenever the browser exposes it.
 * 2. MediaRecorder + Gemini (app/api/voice.py) — the fallback for Safari/iOS
 *    and any browser without SpeechRecognition, which would otherwise have NO
 *    voice input at all.
 *
 * Both paths return the citizen's own words verbatim, in whatever script they
 * spoke — never translated, matching the invariant in agents.md #27 for typed
 * input. The caller (goal page) treats a voice result exactly like typing.
 */

// BCP-47 tags Chrome's cloud recognizer accepts for these languages. Browsers
// without an exact match fall back to their own closest locale.
const RECOGNITION_LOCALE: Record<Language, string> = {
  en: "en-US",
  si: "si-LK",
  ta: "ta-LK",
};

type VoiceStatus = "idle" | "listening" | "processing" | "error";

// Minimal ambient shape for the (non-standard, vendor-prefixed) Web Speech
// API — no @types package ships one, and importing "dom.iterable" doesn't
// cover it.
interface SpeechRecognitionAlternativeLike {
  transcript: string;
}
interface SpeechRecognitionResultLike {
  readonly length: number;
  [index: number]: SpeechRecognitionAlternativeLike;
}
interface SpeechRecognitionEventLike extends Event {
  readonly results: ArrayLike<SpeechRecognitionResultLike>;
}
interface SpeechRecognitionLike extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start(): void;
  stop(): void;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
}
type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionCtor;
    webkitSpeechRecognition?: SpeechRecognitionCtor;
  }
}

function getSpeechRecognitionCtor(): SpeechRecognitionCtor | null {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition ?? window.webkitSpeechRecognition ?? null;
}

// Safari only records mp4/aac; Chrome/Firefox prefer webm/opus. Try the best
// option this browser actually supports rather than hard-coding one.
function pickRecorderMimeType(): string {
  if (typeof MediaRecorder === "undefined") return "";
  for (const type of ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"]) {
    if (MediaRecorder.isTypeSupported(type)) return type;
  }
  return "";
}

interface VoiceInputButtonProps {
  /** Called with the transcript exactly as spoken, plus the detected language when known. */
  onTranscript: (text: string, detectedLanguage?: Language) => void;
  className?: string;
}

export default function VoiceInputButton({ onTranscript, className }: VoiceInputButtonProps) {
  const t = useT();
  const { language } = useLanguage();
  const [status, setStatus] = useState<VoiceStatus>("idle");

  const recognitionRef   = useRef<SpeechRecognitionLike | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef        = useRef<Blob[]>([]);

  // Stop everything on unmount — a citizen navigating away mid-recording
  // should not leave the mic hot or a recognizer running in the background.
  useEffect(() => () => {
    recognitionRef.current?.stop();
    mediaRecorderRef.current?.stream.getTracks().forEach((track) => track.stop());
  }, []);

  useEffect(() => {
    if (status !== "error") return;
    const id = setTimeout(() => setStatus("idle"), 2500);
    return () => clearTimeout(id);
  }, [status]);

  const startNativeRecognition = useCallback((): boolean => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) return false;

    const recognition = new Ctor();
    recognition.lang = RECOGNITION_LOCALE[language];
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onresult = (event) => {
      const last = event.results[event.results.length - 1];
      const transcript = last?.[0]?.transcript?.trim();
      // Native recognition doesn't report a detected language, only a
      // transcript in whatever locale it was told to expect — so the picker's
      // current language is our best signal here, same as typed input before
      // the backend's own normalisation runs.
      if (transcript) onTranscript(transcript, language);
    };
    recognition.onerror = () => setStatus("error");
    recognition.onend = () => setStatus((s) => (s === "listening" ? "idle" : s));

    recognitionRef.current = recognition;
    setStatus("listening");
    recognition.start();
    return true;
  }, [language, onTranscript]);

  const startRecordingFallback = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = pickRecorderMimeType();
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        setStatus("processing");
        try {
          const blob = new Blob(chunksRef.current, { type: mimeType || "audio/webm" });
          const result = await api.transcribeVoice(blob, language);
          if (result.text) onTranscript(result.text, result.language);
          setStatus("idle");
        } catch {
          setStatus("error");
        }
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setStatus("listening");
    } catch {
      // Microphone permission denied, or no getUserMedia support at all.
      setStatus("error");
    }
  }, [language, onTranscript]);

  const handleClick = useCallback(() => {
    if (status === "listening") {
      recognitionRef.current?.stop();
      mediaRecorderRef.current?.stop();
      return;
    }
    if (status === "processing") return;

    if (!startNativeRecognition()) void startRecordingFallback();
  }, [status, startNativeRecognition, startRecordingFallback]);

  const label = status === "listening" ? t("goal.voiceStop") : t("goal.voiceStart");
  const title = status === "error" ? t("goal.voiceError") : label;

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={status === "processing"}
      aria-label={label}
      title={title}
      className={cn(
        "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-all active:scale-90",
        status === "listening"
          ? "bg-(--danger) text-white animate-pulse"
          : status === "error"
            ? "bg-(--danger-light) text-(--danger)"
            : "bg-(--background) text-(--muted-fg) hover:bg-(--border)",
        className,
      )}
    >
      {status === "processing"
        ? <Loader2 size={18} className="animate-spin" />
        : status === "listening"
          ? <Square size={15} fill="currentColor" />
          : <Mic size={18} />}
    </button>
  );
}
