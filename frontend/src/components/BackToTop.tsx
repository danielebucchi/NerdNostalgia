"use client";

import { useEffect, useState } from "react";

/**
 * Bottone "torna su" che appare dopo ~2 schermate di scroll. Centrato in
 * basso per non pestare i FAB (WhatsApp a sinistra, Donazione a destra).
 */
export function BackToTop() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let ticking = false;
    function onScroll() {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        setVisible(window.scrollY > 1200);
        ticking = false;
      });
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (!visible) return null;

  return (
    <button
      type="button"
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
      aria-label="Torna all'inizio"
      className="public-fab fixed bottom-4 left-1/2 -translate-x-1/2 z-40 w-10 h-10 rounded-full bg-white/90 backdrop-blur ring-1 ring-ink/15 shadow-soft text-ink text-lg flex items-center justify-center hover:bg-white transition-all"
    >
      ↑
    </button>
  );
}
