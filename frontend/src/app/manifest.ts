import type { MetadataRoute } from "next";

// Web App Manifest: rende il sito installabile come PWA (Android "Aggiungi
// a schermata Home" con icona + splash; iOS usa apple-touch-icon dal layout).
// Servito da Next su /manifest.webmanifest e linkato in automatico.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "NerdNostalgia",
    short_name: "NerdNostalgia",
    description:
      "Videogiochi vintage, carte Pokémon, Funko Pop e nerderie — compro, vendo, scambio.",
    start_url: "/",
    display: "standalone",
    background_color: "#fff7ed",
    theme_color: "#fff7ed",
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
