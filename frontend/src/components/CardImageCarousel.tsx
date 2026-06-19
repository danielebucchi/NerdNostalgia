"use client";

import { useEffect, useState } from "react";

interface Props {
  images: string[];
  alt: string;
  /** Millisecondi tra un'immagine e la successiva. Default 3000. */
  intervalMs?: number;
  /** Fallback se non c'è nessuna immagine. */
  emptyContent?: React.ReactNode;
}

/**
 * Cicla automaticamente tra le immagini di un articolo direttamente nella card,
 * cosi' l'utente vede tutte le foto senza dover entrare nel dettaglio.
 *
 * - Crossfade morbido tra una foto e la successiva
 * - Si ferma in pausa al passaggio del mouse
 * - Rispetta prefers-reduced-motion (resta sulla copertina)
 * - Indicatori a pallini in basso a destra quando ci sono piu' immagini
 */
export function CardImageCarousel({
  images,
  alt,
  intervalMs = 3000,
  emptyContent,
}: Props) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  useEffect(() => {
    if (images.length <= 1 || paused || reducedMotion) return;
    const id = window.setInterval(() => {
      setIndex((i) => (i + 1) % images.length);
    }, intervalMs);
    return () => window.clearInterval(id);
  }, [images.length, paused, reducedMotion, intervalMs]);

  if (images.length === 0) {
    return (
      <div className="absolute inset-0 flex flex-col items-center justify-center text-ink-soft">
        {emptyContent ?? (
          <>
            <span className="display text-3xl">?</span>
            <span className="text-xs uppercase tracking-wider mt-1">No photo</span>
          </>
        )}
      </div>
    );
  }

  return (
    <div
      className="absolute inset-0"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onTouchStart={() => setPaused(true)}
      onTouchEnd={() => setPaused(false)}
    >
      {images.map((src, i) => (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          key={src}
          src={src}
          alt={i === 0 ? alt : ""}
          aria-hidden={i !== index}
          // Sempre lazy: in griglia con N card, l'eager sulla prima moltiplica N richieste subito.
          // Il browser dara' priorita' alle card visibili comunque.
          loading="lazy"
          decoding="async"
          className="absolute inset-0 w-full h-full object-cover transition-opacity duration-700 ease-in-out"
          style={{ opacity: i === index ? 1 : 0 }}
        />
      ))}

      {images.length > 1 && (
        <div className="absolute bottom-2 right-2 flex gap-1 pointer-events-none">
          {images.map((_, i) => (
            <span
              key={i}
              className={
                "block rounded-full transition-all duration-300 " +
                (i === index
                  ? "w-3 h-1.5 bg-white shadow-soft"
                  : "w-1.5 h-1.5 bg-white/60")
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
