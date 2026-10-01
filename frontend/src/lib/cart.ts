"use client";

import { useCallback, useEffect, useState } from "react";
import { getOrderPublicStatus } from "@/lib/api";
import type { Article } from "@/lib/types";

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

/* ───────────────────── Spese di spedizione ─────────────────────
 * SPEDIZIONE BASE (sul subtotale articoli):
 *   fino a  25,00 €    →   6,00 €
 *   25,01 – 249,99 €   →   6,00 € + 4% (quota % fra 1,00 € e 6,00 €)
 *   da     250,00 €    →  gratis
 *
 * ASSICURAZIONE: +5,70 €, cifra fissa. Proposta già attiva dai 50 € in su,
 * ma il compratore può sempre cambiare idea nei due sensi. Dai 250 € è
 * inclusa nella spedizione gratuita.
 *
 * Copia fedele di backend/src/helpers/shipping.py: cambiando una costante
 * vanno cambiate in entrambi i posti. Qui serve solo a mostrare il totale
 * mentre si sceglie — la cifra che fa fede la calcola il server.
 */

export const FREE_SHIPPING_FROM = 250;
export const INSURED_BY_DEFAULT_FROM = 50;
export const INSURANCE_FEE = 5.7;
const BASE_SHIPPING = 6;
const PERCENT_BAND_FROM = 25;
const PERCENT_RATE = 0.04;
const PERCENT_MIN = 1;
const PERCENT_MAX = 6;

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

/** Spedizione totale: base + eventuale assicurazione. */
export function shippingFor(subtotal: number, insured?: boolean): number {
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

export function cartSubtotal(articles: Article[]): number {
  return articles.reduce((acc, a) => acc + Number(a.price || 0), 0);
}
