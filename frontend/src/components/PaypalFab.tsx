"use client";

import { buildPaypalUrl } from "@/lib/paypal";
import { useSettings } from "@/lib/settings-context";

/**
 * Bottone "Donazione" floating fisso in basso a destra.
 *
 * NB: NON e' gated dal feature flag payments_enabled — anche quando
 * il flusso d'acquisto e' disabilitato (carrello+PayPal-checkout off),
 * la donazione resta sempre disponibile come canale di supporto.
 *
 * Hidden solo se paypal_me non e' configurato (settings runtime, con
 * fallback sulla env di build NEXT_PUBLIC_PAYPAL_ME).
 *
 * z-index 40: sopra contenuto/header (z<40), sotto il CookieBanner (z-50).
 */
export function PaypalFab() {
  const { paypalMe } = useSettings();
  const url = buildPaypalUrl(paypalMe);
  if (!url) return null;

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Donazione tramite PayPal"
      title="Donazione tramite PayPal (scegli 'A un amico o familiare' per evitare commissioni)"
      className="public-fab fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-40 btn btn-paypal shadow-hover text-sm font-bold inline-flex items-center justify-center hover:scale-105 active:scale-100 transition-transform w-12 h-12 p-0 sm:w-auto sm:h-auto sm:px-5 sm:py-3.5 sm:gap-2"
    >
      <span aria-hidden="true" className="inline-flex items-center justify-center w-8 h-8 sm:w-5 sm:h-5 text-3xl sm:text-xl leading-none">❤</span>
      <span className="hidden sm:inline">Donazione</span>
    </a>
  );
}
