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

/**
 * Risolve i markup per (marketplace, category) cercando in ordine:
 *   1) match esatto su category_id
 *   2) match sulla categoria padre (per le sottocategorie)
 *   3) default del marketplace (category_id NULL)
 *   4) fallback hardcoded
 */
export function getMarkupsFromFees(
  fees: MarketplaceFee[],
  marketplace: string,
  categoryId: number | null,
  parentCategoryId: number | null = null,
): number[] {
  if (fees.length === 0) {
    return FALLBACK[marketplace] ?? [];
  }

  if (categoryId != null) {
    const specific = fees.filter(
      (f) => f.marketplace === marketplace && f.category_id === categoryId,
    );
    if (specific.length > 0) return specific.map((f) => Number(f.markup_percent));
  }

  if (parentCategoryId != null) {
    const parent = fees.filter(
      (f) => f.marketplace === marketplace && f.category_id === parentCategoryId,
    );
    if (parent.length > 0) return parent.map((f) => Number(f.markup_percent));
  }

  const defaults = fees.filter(
    (f) => f.marketplace === marketplace && f.category_id == null,
  );
  if (defaults.length > 0) return defaults.map((f) => Number(f.markup_percent));

  return FALLBACK[marketplace] ?? [];
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
