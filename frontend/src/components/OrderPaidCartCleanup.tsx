"use client";

import { useEffect } from "react";
import { syncPendingOrder } from "@/lib/cart";

/**
 * Svuota il carrello sulla pagina di ringraziamento (ritorno da Stripe).
 *
 * Il redirect del browser puo' arrivare prima del webhook che marca l'ordine
 * PAID: per questo riprova qualche volta invece di arrendersi al primo "non
 * ancora pagato". Se non ci riesce nemmeno dopo i tentativi non fa nulla —
 * ci pensera' l'header al prossimo caricamento di pagina.
 */
const RETRIES = 5;
const DELAY_MS = 2000;

export function OrderPaidCartCleanup() {
  useEffect(() => {
    let cancelled = false;

    (async () => {
      for (let attempt = 0; attempt < RETRIES; attempt++) {
        const outcome = await syncPendingOrder();
        if (cancelled || outcome === "paid" || outcome === "cancelled") return;
        await new Promise((r) => setTimeout(r, DELAY_MS));
        if (cancelled) return;
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return null;
}
