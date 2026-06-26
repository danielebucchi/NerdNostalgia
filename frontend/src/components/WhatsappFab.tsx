"use client";

/**
 * FAB fisso in basso a sinistra che porta al gruppo WhatsApp NerdNostalgia.
 * Speculare a PaypalFab (bottom-right) — sempre visibile su tutte le pagine
 * pubbliche, canale di contatto + community alternativo all'email.
 *
 * z-index 40: sopra contenuto/header (z<40), sotto il CookieBanner (z-50).
 */
const WHATSAPP_GROUP_URL =
  "https://chat.whatsapp.com/GBvrghMizxfFRywmRIOrSq?s=cl&p=i&ilr=0";

export function WhatsappFab() {
  return (
    <a
      href={WHATSAPP_GROUP_URL}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Entra nel gruppo WhatsApp NerdNostalgia"
      title="Entra nel gruppo WhatsApp NerdNostalgia"
      className="fixed bottom-4 left-4 sm:bottom-6 sm:left-6 z-40 btn btn-whatsapp shadow-hover inline-flex items-center justify-center hover:scale-105 active:scale-100 transition-transform w-12 h-12 p-0"
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/whatsapp.png" alt="" className="w-8 h-8 object-contain" />
    </a>
  );
}
