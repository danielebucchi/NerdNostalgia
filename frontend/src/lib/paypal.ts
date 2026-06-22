/**
 * Costruisce un link paypal.me/{handle}/{amount}{currency}.
 * Se NEXT_PUBLIC_PAYPAL_ME non e' settato (env var build-time), ritorna null
 * → i bottoni PayPal si nascondono automaticamente.
 *
 * Setta NEXT_PUBLIC_PAYPAL_ME=tuohandle nel .env per attivarli.
 */
const PAYPAL_HANDLE = (process.env.NEXT_PUBLIC_PAYPAL_ME ?? "").trim();

export function paypalUrl(
  amount?: number | string | null,
  currency: string = "EUR",
): string | null {
  if (!PAYPAL_HANDLE) return null;
  const base = `https://paypal.me/${encodeURIComponent(PAYPAL_HANDLE)}`;
  if (amount == null || amount === "") return base;
  const n = typeof amount === "number" ? amount : Number(amount);
  if (!Number.isFinite(n) || n <= 0) return base;
  // Formato amount accettato da paypal.me: numero "puro" + ISO code.
  // Usa punto come separatore decimale e max 2 decimali.
  const formatted = n.toFixed(2);
  return `${base}/${formatted}${currency.toUpperCase()}`;
}

export function paypalEnabled(): boolean {
  return PAYPAL_HANDLE.length > 0;
}
