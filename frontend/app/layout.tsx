import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "HelpLK AI — Your Agentic Citizen Services Copilot",
  description:
    "Sri Lanka's AI-powered citizen services copilot. Describe your government need and let intelligent agents plan, verify, and guide you step by step.",
  keywords: ["Sri Lanka", "government services", "AI", "citizen services", "NIC", "passport", "agentic AI"],
};

export const viewport: Viewport = {
  themeColor: "#14B8A6",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="min-h-dvh flex flex-col antialiased">{children}</body>
    </html>
  );
}
