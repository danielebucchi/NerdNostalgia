"use client";

import { paypalUrl } from "@/lib/paypal";

/**
 * Bottone PayPal floating fisso in basso a destra.
 * Importo libero (l'utente lo inserisce su paypal.me).
 *
 * z-index 40: sopra contenuto/header (z<40), sotto il CookieBanner (z-50)
 * cosi' non si sovrappone all'avviso cookie al primo accesso.
 *
 * Hidden se NEXT_PUBLIC_PAYPAL_ME non e' configurato.
 */
export function PaypalFab() {
  const url = paypalUrl();
  if (!url) return null;

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Paga con PayPal — seleziona Amico/Familiare per evitare commissioni"
      title="Su PayPal scegli 'A un amico o familiare' per evitare le commissioni"
      className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-40 btn btn-paypal shadow-hover px-5 py-3.5 text-sm font-bold inline-flex items-center gap-2 hover:scale-105 active:scale-100 transition-transform"
    >
      <span aria-hidden="true" className="text-lg">💳</span>
      <span className="hidden sm:inline">PayPal · Amico/Familiare</span>
      <span className="sm:hidden">PayPal</span>
    </a>
  );
}
