"use client";

import { buildPaypalUrl } from "@/lib/paypal";
import { useSettings } from "@/lib/settings-context";

interface Props {
  /** Importo da prefillare nel link paypal.me. Lascia vuoto per importo libero. */
  amount?: number | string | null;
  currency?: string;
  className?: string;
  /** Testo dopo il logo. Default: "Paga con PayPal" */
  label?: string;
}

/**
 * Bottone CTA inline che apre paypal.me con importo prefillato (se passato).
 * Se paypal_me non e' configurato (settings/env), ritorna null (no render).
 */
export function PaypalButton({
  amount,
  currency = "EUR",
  className = "",
  label = "Paga con PayPal",
}: Props) {
  const { paypalMe } = useSettings();
  const url = buildPaypalUrl(paypalMe, amount, currency);
  if (!url) return null;

  const ariaAmount = amount ? ` (${Number(amount).toFixed(2)} ${currency})` : "";
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`${label}${ariaAmount}`}
      className={`btn btn-paypal text-sm font-bold px-4 py-2.5 inline-flex items-center gap-2 ${className}`}
    >
      <span>{label}</span>
      <span aria-hidden="true">→</span>
    </a>
  );
}
