"use client";

import { useCallback, useEffect, useState } from "react";
import type { Article } from "@/lib/types";

const STORAGE_KEY = "nn:cart:v1";
const EVENT = "nn:cart-change";

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

/**
 * Calcolo spedizione aggregata. Allineato col backend (orders.py):
 * MAX delle shipping_price dei pezzi nel pacco. Senza shipping → 5€.
 */
export function aggregateShipping(articles: Article[]): number {
  if (articles.length === 0) return 0;
  const ships = articles.map((a) =>
    a.shipping_price ? Number(a.shipping_price) : 5,
  );
  return Math.max(...ships);
}

export function cartSubtotal(articles: Article[]): number {
  return articles.reduce((acc, a) => acc + Number(a.price || 0), 0);
}
