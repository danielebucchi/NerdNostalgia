/* Spese di spedizione, senza dipendenze dal browser: le usano il carrello
 * (lib/cart.ts) e le pagine server, per esempio i dati strutturati della
 * scheda articolo letti da Google. */

/* ───────────────────── Spese di spedizione ─────────────────────
 * SPEDIZIONE BASE (sul subtotale articoli):
 *   fino a  25,00 €    →   6,21 €
 *   25,01 – 249,99 €   →   6,21 € + 4% (quota % fra 1,00 € e 6,21 €)
 *   da     250,00 €    →  gratis
 *
 * ASSICURAZIONE: +5,90 €, cifra fissa. Proposta già attiva dai 50 € in su,
 * ma il compratore può sempre cambiare idea nei due sensi. Dai 250 € è
 * inclusa nella spedizione gratuita.
 *
 * Copia fedele di backend/src/helpers/shipping.py: cambiando una costante
 * vanno cambiate in entrambi i posti. Qui serve solo a mostrare il totale
 * mentre si sceglie — la cifra che fa fede la calcola il server.
 */

export const FREE_SHIPPING_FROM = 250;
export const INSURED_BY_DEFAULT_FROM = 50;
export const INSURANCE_FEE = 5.9;
const BASE_SHIPPING = 6.21;
const PERCENT_BAND_FROM = 25;
const PERCENT_RATE = 0.04;
const PERCENT_MIN = 1;
const PERCENT_MAX = 6.21;

function round2(n: number): number {
  return Math.round(n * 100) / 100;
}

/** Spedizione senza assicurazione. */
export function baseShippingFor(subtotal: number): number {
  if (!Number.isFinite(subtotal) || subtotal <= 0) return BASE_SHIPPING;
  if (subtotal >= FREE_SHIPPING_FROM) return 0;
  if (subtotal <= PERCENT_BAND_FROM) return BASE_SHIPPING;
  const variable = Math.min(
    Math.max(round2(subtotal * PERCENT_RATE), PERCENT_MIN),
    PERCENT_MAX,
  );
  return round2(BASE_SHIPPING + variable);
}

/** Assicurazione proposta già attiva? Sì, dai 50 € in su. */
export function defaultInsured(subtotal: number): boolean {
  return Number.isFinite(subtotal) && subtotal >= INSURED_BY_DEFAULT_FROM;
}

/** Sopra la soglia di spedizione gratuita l'assicurazione è inclusa: non si
 *  può togliere (un pacco da 250 € non viaggia scoperto) e non si paga. */
export function insuranceIsIncluded(subtotal: number): boolean {
  return Number.isFinite(subtotal) && subtotal >= FREE_SHIPPING_FROM;
}

/** Quanto costa l'assicurazione su questo ordine. */
export function insuranceFeeFor(subtotal: number, insured: boolean): number {
  if (!insured || insuranceIsIncluded(subtotal)) return 0;
  return INSURANCE_FEE;
}

/** Spedizione totale: base + eventuale assicurazione.
 *  `freeAll` è la promozione "spedizione gratuita su tutto" dalle settings:
 *  azzera la riga intera, assicurazione compresa. */
export function shippingFor(
  subtotal: number,
  insured?: boolean,
  freeAll = false,
): number {
  if (freeAll) return 0;
  const chosen = insuranceIsIncluded(subtotal)
    ? true
    : insured ?? defaultInsured(subtotal);
  return round2(baseShippingFor(subtotal) + insuranceFeeFor(subtotal, chosen));
}

/** Quanto manca alla spedizione gratuita. Zero se ci siamo già. */
export function missingForFreeShipping(subtotal: number): number {
  if (!Number.isFinite(subtotal) || subtotal >= FREE_SHIPPING_FROM) return 0;
  return round2(FREE_SHIPPING_FROM - Math.max(0, subtotal));
}
