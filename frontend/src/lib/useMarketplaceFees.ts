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
