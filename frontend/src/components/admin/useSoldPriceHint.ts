"use client";

/**
 * Memoria prezzi: dato un titolo, cerca tra gli item GIA' VENDUTI con
 * titolo simile e restituisce un hint tipo «"Pokemon Rosso GB" venduto
 * a 35€ (dic 2026)». Debounce 500ms, best-effort (errori silenziati).
 */
import { useEffect, useState } from "react";
import { adminApi } from "@/lib/admin-api";
import type { InventoryItem, InventoryListResponse } from "@/lib/types";

export function useSoldPriceHint(title: string): string | null {
  const [hint, setHint] = useState<string | null>(null);

  useEffect(() => {
    const q = title.trim();
    if (q.length < 4) {
      setHint(null);
      return;
    }
    let cancelled = false;
    const t = setTimeout(async () => {
      try {
        const data = await adminApi.get<InventoryListResponse>(
          `/api/inventory/?search=${encodeURIComponent(q)}&sold_only=true&limit=3`,
        );
        if (cancelled) return;
        const best: InventoryItem | undefined = data.items.find(
          (i) => i.sale_price != null,
        );
        if (!best || best.sale_price == null) {
          setHint(null);
          return;
        }
        const when = best.sold_date
          ? new Date(best.sold_date).toLocaleDateString("it-IT", {
              month: "short",
              year: "numeric",
            })
          : null;
        setHint(
          `💡 "${best.title}" venduto a €${Number(best.sale_price).toFixed(0)}` +
            (when ? ` (${when})` : ""),
        );
      } catch {
        if (!cancelled) setHint(null);
      }
    }, 500);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [title]);

  return hint;
}
