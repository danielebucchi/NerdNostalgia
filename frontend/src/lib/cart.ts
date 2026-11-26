"use client";

import { useCallback, useEffect, useState } from "react";
import { getOrderPublicStatus } from "@/lib/api";
import type { Article } from "@/lib/types";

// Le spese di spedizione stanno in lib/shipping.ts (servono anche lato
// server); qui restano esportate per chi le importa dal carrello.
export * from "@/lib/shipping";

const STORAGE_KEY = "nn:cart:v1";
const EVENT = "nn:cart-change";
const PENDING_KEY = "nn:pending-order:v1";
/** Dopo 30 giorni un ordine in sospeso non ci interessa piu'. */
const PENDING_TTL_MS = 30 * 24 * 60 * 60 * 1000;

export interface CartItem {
  article_id: number;
  added_at: number;
}

function readItems(): CartItem[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(
      (x): x is CartItem =>
        x && typeof x.article_id === "number" && Number.isInteger(x.article_id),
    );
  } catch {
    return [];
  }
}

function writeItems(items: CartItem[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  window.dispatchEvent(new Event(EVENT));
}

/**
 * Carrello persistente in localStorage. Solo article_id (i dati live li
 * recuperiamo dall'API per non mostrare prezzi vecchi se cambiano).
 */
export function useCart() {
  const [items, setItems] = useState<CartItem[]>([]);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setItems(readItems());
    setHydrated(true);
    function onChange() {
      setItems(readItems());
    }
    window.addEventListener(EVENT, onChange);
    window.addEventListener("storage", onChange);
    return () => {
      window.removeEventListener(EVENT, onChange);
      window.removeEventListener("storage", onChange);
    };
  }, []);

  const has = useCallback(
    (id: number) => items.some((it) => it.article_id === id),
    [items],
  );

  const add = useCallback((id: number) => {
    const current = readItems();
    if (current.some((it) => it.article_id === id)) return;
    writeItems([...current, { article_id: id, added_at: Date.now() }]);
  }, []);

  const remove = useCallback((id: number) => {
    const current = readItems();
    const next = current.filter((it) => it.article_id !== id);
    if (next.length !== current.length) writeItems(next);
  }, []);

  const toggle = useCallback((id: number) => {
    const current = readItems();
    if (current.some((it) => it.article_id === id)) {
      writeItems(current.filter((it) => it.article_id !== id));
    } else {
      writeItems([...current, { article_id: id, added_at: Date.now() }]);
    }
  }, []);

  const clear = useCallback(() => {
    writeItems([]);
  }, []);

  return { items, has, add, remove, toggle, clear, hydrated, count: items.length };
}

/* ───────────────────── Ordine in sospeso ─────────────────────
 * Il carrello NON si svuota quando l'ordine viene creato: a quel punto il
 * compratore non ha ancora pagato (con PayPal se ne va su un'altra scheda e
 * non torna necessariamente). Teniamo da parte id + token dell'ordine e
 * svuotiamo solo quando il backend conferma che risulta pagato.
 */

export interface PendingOrder {
  id: number;
  token: string;
  created_at: number;
}

export function readPendingOrder(): PendingOrder | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(PENDING_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (
      !parsed ||
      typeof parsed.id !== "number" ||
      typeof parsed.token !== "string" ||
      typeof parsed.created_at !== "number"
    ) {
      return null;
    }
    if (Date.now() - parsed.created_at > PENDING_TTL_MS) {
      window.localStorage.removeItem(PENDING_KEY);
      return null;
    }
    return parsed as PendingOrder;
  } catch {
    return null;
  }
}

export function setPendingOrder(id: number, token: string | null): void {
  if (typeof window === "undefined" || !token) return;
  window.localStorage.setItem(
    PENDING_KEY,
    JSON.stringify({ id, token, created_at: Date.now() }),
  );
}

export function clearPendingOrder(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(PENDING_KEY);
  window.dispatchEvent(new Event(EVENT));
}

export type PendingOrderOutcome = "paid" | "cancelled" | "pending" | "unknown";

/**
 * Chiede al backend com'e' finito l'ordine in sospeso e agisce:
 *  - pagato    → svuota il carrello e dimentica l'ordine;
 *  - annullato → dimentica l'ordine, il carrello resta (puo' riprovare);
 *  - in attesa → non tocca niente;
 *  - unknown   → rete giu' o nessun ordine in sospeso: non tocca niente.
 *
 * "unknown" non e' "non pagato": al minimo dubbio il carrello resta pieno.
 */
export async function syncPendingOrder(): Promise<PendingOrderOutcome> {
  const pending = readPendingOrder();
  if (!pending) return "unknown";

  const status = await getOrderPublicStatus(pending.id, pending.token);
  if (!status) return "unknown";
  if (status.paid) {
    writeItems([]);
    clearPendingOrder();
    return "paid";
  }
  if (status.cancelled) {
    clearPendingOrder();
    return "cancelled";
  }
  return "pending";
}

// Una sola verifica per caricamento di pagina: l'hook sta nell'header, che
// monta due istanze (desktop + mobile), e non vogliamo due chiamate uguali.
let checkedThisPageLoad = false;

/** Verifica una tantum all'apertura di una pagina qualsiasi (sta nell'header). */
export function usePaidOrderCleanup(): void {
  useEffect(() => {
    if (checkedThisPageLoad) return;
    if (!readPendingOrder()) return;
    checkedThisPageLoad = true;
    void syncPendingOrder();
  }, []);
}

export function cartSubtotal(articles: Article[]): number {
  return articles.reduce((acc, a) => acc + Number(a.price || 0), 0);
}
