import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Noto_Sans_Sinhala, Noto_Sans_Tamil } from "next/font/google";
import ClientShell from "@/components/ClientShell";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

// Geist carries no Sinhala or Tamil glyphs, so without these the UI renders as
// tofu on any system lacking a local Noto. Not preloaded: an English reader
// should not pay for two extra families, and `swap` keeps first paint fast.
const notoSinhala = Noto_Sans_Sinhala({
  variable: "--font-noto-sinhala",
  subsets: ["sinhala"],
  display: "swap",
  preload: false,
});
const notoTamil = Noto_Sans_Tamil({
  variable: "--font-noto-tamil",
  subsets: ["tamil"],
  display: "swap",
  preload: false,
});

export const metadata: Metadata = {
  title: "HelpLK — Government Services Guide",
  description:
    "Free step-by-step guide for Sri Lanka government services. Get help with passports, NIC, driving licences, birth certificates and more.",
  keywords: ["Sri Lanka", "government services", "passport", "NIC", "driving licence", "birth certificate"],
};

export const viewport: Viewport = {
  themeColor: "#1D4ED8",
  width: "device-width",
  initialScale: 1,
};

/**
 * Applies the stored/URL language to <html lang> BEFORE first paint.
 *
 * Doing this in an effect instead would paint one frame as lang="en" with
 * Sinhala text: screen readers announce the wrong language and the
 * `html[lang="si"]` line-height rule in globals.css would not apply until
 * after hydration, causing a visible reflow.
 */
const LANG_BOOTSTRAP = `
(function(){try{
  var u=new URLSearchParams(location.search).get('lang');
  var s=localStorage.getItem('helplk_lang');
  var n=(navigator.language||'').slice(0,2).toLowerCase();
  var ok={en:1,si:1,ta:1};
  var l=ok[u]?u:ok[s]?s:ok[n]?n:'en';
  localStorage.setItem('helplk_lang',l);
  document.documentElement.lang=l;
}catch(e){}})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${notoSinhala.variable} ${notoTamil.variable}`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: LANG_BOOTSTRAP }} />
      </head>
      <body className="min-h-dvh flex flex-col antialiased">
        <ClientShell>{children}</ClientShell>
      </body>
    </html>
  );
}
