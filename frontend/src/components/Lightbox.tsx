"use client";

import { useCallback, useEffect, useState } from "react";

interface Props {
  images: string[];
  startIndex?: number;
  alt: string;
  open: boolean;
  onClose: () => void;
}

/**
 * Lightbox modale full-screen per la galleria articolo. Supporta:
 *  - frecce ← → da tastiera, ESC per chiudere
 *  - swipe touch (orizzontale > 60px)
 *  - click sul backdrop per chiudere
 *  - pallini indicatori
 *  - blocca lo scroll del body mentre è aperto
 */
export function Lightbox({ images, startIndex = 0, alt, open, onClose }: Props) {
  const [index, setIndex] = useState(startIndex);
  const [touchStartX, setTouchStartX] = useState<number | null>(null);

  useEffect(() => {
    if (open) setIndex(startIndex);
  }, [open, startIndex]);

  const next = useCallback(() => {
    setIndex((i) => (i + 1) % images.length);
  }, [images.length]);

  const prev = useCallback(() => {
    setIndex((i) => (i - 1 + images.length) % images.length);
  }, [images.length]);

  useEffect(() => {
    if (!open) return;

    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight") next();
      else if (e.key === "ArrowLeft") prev();
    }
    window.addEventListener("keydown", onKey);

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, next, prev, onClose]);

  if (!open || images.length === 0) return null;

  function handleTouchStart(e: React.TouchEvent) {
    setTouchStartX(e.touches[0].clientX);
  }

  function handleTouchEnd(e: React.TouchEvent) {
    if (touchStartX == null) return;
    const dx = e.changedTouches[0].clientX - touchStartX;
    if (Math.abs(dx) > 60) {
      if (dx < 0) next();
      else prev();
    }
    setTouchStartX(null);
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 bg-ink/85 backdrop-blur-md flex items-center justify-center"
      onClick={onClose}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onClose();
        }}
        className="absolute top-4 right-4 w-11 h-11 rounded-full bg-white/15 hover:bg-white/30 backdrop-blur-md text-white text-xl flex items-center justify-center ring-1 ring-white/30 transition-all"
        aria-label="Chiudi"
      >
        ✕
      </button>

      {images.length > 1 && (
        <>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              prev();
            }}
            className="absolute left-4 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-white/15 hover:bg-white/30 backdrop-blur-md text-white text-2xl flex items-center justify-center ring-1 ring-white/30 transition-all"
            aria-label="Precedente"
          >
            ‹
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              next();
            }}
            className="absolute right-4 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-white/15 hover:bg-white/30 backdrop-blur-md text-white text-2xl flex items-center justify-center ring-1 ring-white/30 transition-all"
            aria-label="Successiva"
          >
            ›
          </button>
        </>
      )}

      <div
        className="max-w-[92vw] max-h-[88vh] flex items-center justify-center"
        onClick={(e) => e.stopPropagation()}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={images[index]}
          alt={alt}
          className="max-w-full max-h-[88vh] object-contain rounded-lg shadow-2xl"
        />
      </div>

      {images.length > 1 && (
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-1.5 pointer-events-none">
          {images.map((_, i) => (
            <span
              key={i}
              className={
                "block rounded-full transition-all duration-300 " +
                (i === index
                  ? "w-6 h-2 bg-white"
                  : "w-2 h-2 bg-white/50")
              }
            />
          ))}
        </div>
      )}

      <div className="absolute bottom-2 right-4 text-xs text-white/70 pointer-events-none hidden sm:block">
        {index + 1} / {images.length}
      </div>
    </div>
  );
}
