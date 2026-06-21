import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import ClientShell from "@/components/ClientShell";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

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

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="min-h-dvh flex flex-col antialiased">
        {children}
        <ClientShell />
      </body>
    </html>
  );
}
