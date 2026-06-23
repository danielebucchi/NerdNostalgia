"use client";

import { paypalUrl } from "@/lib/paypal";

/**
 * Bottone "Donazione" floating fisso in basso a destra.
 *
 * NB: NON e' gated dal feature flag PAYMENTS_ENABLED — anche quando
 * il flusso d'acquisto e' disabilitato (carrello+PayPal-checkout off),
 * la donazione resta sempre disponibile come canale di supporto.
 *
 * Hidden solo se NEXT_PUBLIC_PAYPAL_ME non e' configurato.
 *
 * z-index 40: sopra contenuto/header (z<40), sotto il CookieBanner (z-50).
 */
export function PaypalFab() {
  const url = paypalUrl();
  if (!url) return null;

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Donazione tramite PayPal"
      title="Donazione tramite PayPal (scegli 'A un amico o familiare' per evitare commissioni)"
      className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-40 btn btn-paypal shadow-hover px-5 py-3.5 text-sm font-bold inline-flex items-center gap-2 hover:scale-105 active:scale-100 transition-transform"
    >
      <span aria-hidden="true" className="text-lg">❤</span>
      <span>Donazione</span>
    </a>
  );
}
