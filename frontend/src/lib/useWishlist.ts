"use client";

import { useEffect, useState, useCallback } from "react";

const STORAGE_KEY = "nn:wishlist:v1";
const EVENT = "nn:wishlist-change";

function readIds(): number[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((x) => typeof x === "number");
  } catch {
    return [];
  }
}

function writeIds(ids: number[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  window.dispatchEvent(new Event(EVENT));
}

/**
 * Wishlist persistita in localStorage. Funziona senza login.
 * Tutti i componenti che usano il hook si sincronizzano via custom event.
 */
export function useWishlist() {
  const [ids, setIds] = useState<number[]>([]);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setIds(readIds());
    setHydrated(true);
    function onChange() {
      setIds(readIds());
    }
    window.addEventListener(EVENT, onChange);
    window.addEventListener("storage", onChange);
    return () => {
      window.removeEventListener(EVENT, onChange);
      window.removeEventListener("storage", onChange);
    };
  }, []);

  const has = useCallback((id: number) => ids.includes(id), [ids]);

  const toggle = useCallback((id: number) => {
    const current = readIds();
    const next = current.includes(id)
      ? current.filter((x) => x !== id)
      : [...current, id];
    writeIds(next);
  }, []);

  const remove = useCallback((id: number) => {
    const current = readIds();
    if (current.includes(id)) {
      writeIds(current.filter((x) => x !== id));
    }
  }, []);

  const clear = useCallback(() => {
    writeIds([]);
  }, []);

  return { ids, has, toggle, remove, clear, hydrated, count: ids.length };
}
