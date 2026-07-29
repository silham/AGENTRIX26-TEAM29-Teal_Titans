import type { MetadataRoute } from "next";

/**
 * Web app manifest — what makes HelpLK installable to a home screen.
 *
 * Deliberately NOT localized: `manifest.ts` is a server route with no access to
 * the citizen's stored language (it lives in localStorage), and the installed
 * app name is baked in at install time anyway. The name is kept short and
 * script-neutral so it reads the same for every citizen.
 *
 * Two icon purposes, because Android treats them differently: "any" is drawn
 * as-is, while "maskable" is clipped to a circle/squircle — a full-bleed glyph
 * loses its edges, so the maskable files carry their own safe-zone padding.
 */
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "HelpLK — Sri Lanka Government Services Guide",
    short_name: "HelpLK",
    description:
      "Step-by-step guidance for Sri Lankan government services — passports, NIC, driving licences and birth certificates — in Sinhala, Tamil and English.",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#EEF2FF", // matches --background, so the splash matches the app
    theme_color: "#1D4ED8",      // matches --primary, so the status bar matches the UI
    categories: ["government", "productivity", "utilities"],
    lang: "en",
    dir: "ltr",                  // Sinhala and Tamil are both left-to-right
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      {
        src: "/icon-maskable-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/icon-maskable-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
    shortcuts: [
      { name: "Start a new plan", url: "/goal" },
      { name: "My plans", url: "/dashboard" },
    ],
  };
}
