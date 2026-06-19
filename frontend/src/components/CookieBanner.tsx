"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const STORAGE_KEY = "nn:cookie-notice:v1";

// Informativa, NON banner di consenso: il sito usa solo localStorage tecnico
// (preferiti + token admin). Niente analytics, niente terze parti, niente
// profilazione → ai sensi delle Linee Guida del Garante (10 giugno 2021) il
// consenso preventivo non e' richiesto. Mostriamo comunque un avviso
// informativo dismissibile per trasparenza.
export function CookieBanner() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    try {
      if (window.localStorage.getItem(STORAGE_KEY) !== "1") {
        setVisible(true);
      }
    } catch {
      // localStorage non accessibile (private mode su alcuni browser): nascondi
    }
  }, []);

  if (!visible) return null;

  const dismiss = () => {
    try {
      window.localStorage.setItem(STORAGE_KEY, "1");
    } catch {
      // ignora
    }
    setVisible(false);
  };

  return (
    <div
      role="dialog"
      aria-live="polite"
      aria-label="Informativa sull'uso dei dati"
      className="fixed inset-x-0 bottom-0 z-50 px-4 pb-4 sm:px-6 sm:pb-6 pointer-events-none"
    >
      <div className="mx-auto max-w-3xl bg-white/95 backdrop-blur rounded-2xl shadow-hover ring-1 ring-ink/15 p-4 sm:p-5 pointer-events-auto">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4">
          <p className="text-sm text-ink-soft leading-relaxed flex-1">
            <span className="text-ink font-semibold">Una nota veloce.</span>{" "}
            Salviamo nel tuo browser solo dati tecnici (preferiti, sessione
            admin) — niente cookie di profilazione né terze parti. Dettagli
            nella{" "}
            <Link
              href="/cookie-policy"
              className="text-lilac-deep font-semibold hover:underline"
            >
              Cookie Policy
            </Link>{" "}
            e nella{" "}
            <Link
              href="/privacy"
              className="text-lilac-deep font-semibold hover:underline"
            >
              Privacy
            </Link>
            .
          </p>
          <button
            type="button"
            onClick={dismiss}
            className="btn btn-primary text-sm whitespace-nowrap self-end sm:self-auto"
          >
            Ho capito
          </button>
        </div>
      </div>
    </div>
  );
}
