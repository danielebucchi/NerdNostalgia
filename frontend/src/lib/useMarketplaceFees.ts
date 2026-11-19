"use client";

import { useEffect, useState } from "react";
import { PUBLIC_API_BASE } from "@/lib/api";
import type { MarketplaceFee } from "@/lib/types";

/** Hard-fallback markups se il backend e' irraggiungibile. */
const FALLBACK: Record<string, number[]> = {
  vinted: [0, 5],
  ebay: [11],
};

interface State {
  fees: MarketplaceFee[];
  loading: boolean;
  error: string | null;
  reload: () => void;
}

export function useMarketplaceFees(): State {
  const [fees, setFees] = useState<MarketplaceFee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [bump, setBump] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetch(`${PUBLIC_API_BASE}/api/marketplace-fees/`, { cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => {
        if (!cancelled) setFees(d.items || []);
      })
      .catch((err) => {
        if (!cancelled) setError(String(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [bump]);

  return { fees, loading, error, reload: () => setBump((b) => b + 1) };
}

/* ───────────────── Commissioni del canale di vendita diretta ─────────────────
 * "sito" = quello che tratteni tu vendendo dal tuo sito, cioe' la commissione
 * del gateway di pagamento (PayPal, Stripe). A differenza dei marketplace ha
 * anche una quota FISSA per transazione, che sugli articoli economici pesa piu'
 * della percentuale.
 */

export const SITE_MARKETPLACE = "sito";

export interface ResolvedFee {
  percent: number;
  fixed: number;
}

/**
 * Commissione per (marketplace, categoria), con la stessa cascata dei markup:
 * categoria esatta → categoria padre → default del marketplace. Null se non e'
 * configurata nessuna commissione: in quel caso non inventiamo un valore, non
 * mostriamo il suggerimento e basta.
 */
export function resolveFee(
  fees: MarketplaceFee[],
  marketplace: string,
  categoryId: number | null,
  parentCategoryId: number | null = null,
): ResolvedFee | null {
  const pick = (list: MarketplaceFee[]): ResolvedFee | null => {
    const f = list[0];
    if (!f) return null;
    return { percent: Number(f.markup_percent), fixed: Number(f.fixed_fee ?? 0) };
  };

  const of = (predicate: (f: MarketplaceFee) => boolean) =>
    fees.filter((f) => f.marketplace === marketplace && predicate(f));

  if (categoryId != null) {
    const hit = pick(of((f) => f.category_id === categoryId));
    if (hit) return hit;
  }
  if (parentCategoryId != null) {
    const hit = pick(of((f) => f.category_id === parentCategoryId));
    if (hit) return hit;
  }
  return pick(of((f) => f.category_id == null));
}

/**
 * Prezzo di vendita necessario per incassare `net` al netto della commissione.
 *
 * La commissione si calcola sul LORDO, quindi non basta aggiungere la
 * percentuale al netto: va risolta l'equazione
 *     lordo - (lordo * p + fisso) = net
 * da cui  lordo = (net + fisso) / (1 - p).
 * Arrotondiamo al centesimo superiore: meglio incassare un centesimo in piu'
 * che scoprire di averci rimesso.
 */
export function grossUpPrice(net: number, fee: ResolvedFee): number | null {
  if (!Number.isFinite(net) || net <= 0) return null;
  const p = fee.percent / 100;
  if (!(p >= 0) || p >= 1) return null;
  const gross = (net + fee.fixed) / (1 - p);
  return Math.ceil(gross * 100) / 100;
}

/** Quanto resta in tasca vendendo a `gross`. Negativo se la commissione se lo mangia. */
export function netAfterFee(gross: number, fee: ResolvedFee): number | null {
  if (!Number.isFinite(gross) || gross <= 0) return null;
  return Math.round((gross - (gross * fee.percent) / 100 - fee.fixed) * 100) / 100;
}


/**
 * Le commissioni complete (percentuale + quota fissa) per (marketplace,
 * categoria), cercando in ordine: categoria esatta, categoria padre,
 * default del marketplace, ripiego fisso (FALLBACK). Ogni voce diventa un
 * pulsante "copri la commissione" nei riquadri marketplace.
 */
export function getFeesFor(
  fees: MarketplaceFee[],
  marketplace: string,
  categoryId: number | null,
  parentCategoryId: number | null = null,
): ResolvedFee[] {
  const of = (predicate: (f: MarketplaceFee) => boolean) =>
    fees
      .filter((f) => f.marketplace === marketplace && predicate(f))
      .map((f) => ({ percent: Number(f.markup_percent), fixed: Number(f.fixed_fee ?? 0) }));
  if (fees.length === 0) return (FALLBACK[marketplace] ?? []).map((percent) => ({ percent, fixed: 0 }));
  for (const livello of [
    categoryId != null ? of((f) => f.category_id === categoryId) : [],
    parentCategoryId != null ? of((f) => f.category_id === parentCategoryId) : [],
    of((f) => f.category_id == null),
  ]) {
    if (livello.length > 0) return livello;
  }
  return (FALLBACK[marketplace] ?? []).map((percent) => ({ percent, fixed: 0 }));
}

/** eBay non accetta inserzioni a prezzo fisso sotto 1 euro. */
const MINIMO: Record<string, number> = { ebay: 1 };

/**
 * Prezzo sul marketplace che, tolta la commissione, lascia `base` in tasca
 * (grossUpPrice), mai sotto il minimo del marketplace. Stringa "12.34"
 * pronta per il campo prezzo; "" se il prezzo base non e' valido.
 */
export function priceCoveringFee(base: string | number, fee: ResolvedFee, marketplace: string): string {
  const gross = grossUpPrice(Number(base), fee);
  if (gross == null) return "";
  return Math.max(gross, MINIMO[marketplace] ?? 0).toFixed(2);
}

/** Etichetta del pulsante: "+6.5% +0,35 €", o "uguale" senza commissione. */
export function feeLabel(fee: ResolvedFee): string {
  if (!fee.percent && !fee.fixed) return "uguale";
  const parti = [];
  if (fee.percent) parti.push(`+${fee.percent}%`);
  if (fee.fixed) parti.push(`+${fee.fixed.toFixed(2).replace(".", ",")} €`);
  return parti.join(" ");
}
