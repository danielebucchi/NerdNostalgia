/**
 * Builder puro per link paypal.me/{handle}/{amount}{currency}.
 *
 * L'handle arriva dalle settings runtime (useSettings().paypalMe — con
 * fallback sulla env di build NEXT_PUBLIC_PAYPAL_ME). Se l'handle e' vuoto
 * ritorna null → i bottoni PayPal si nascondono automaticamente.
 */
export function buildPaypalUrl(
  handle: string,
  amount?: number | string | null,
  currency: string = "EUR",
): string | null {
  const h = handle.trim();
  if (!h) return null;
  const base = `https://paypal.me/${encodeURIComponent(h)}`;
  if (amount == null || amount === "") return base;
  const n = typeof amount === "number" ? amount : Number(amount);
  if (!Number.isFinite(n) || n <= 0) return base;
  // Formato amount accettato da paypal.me: numero "puro" + ISO code.
  // Usa punto come separatore decimale e max 2 decimali.
  const formatted = n.toFixed(2);
  return `${base}/${formatted}${currency.toUpperCase()}`;
}
