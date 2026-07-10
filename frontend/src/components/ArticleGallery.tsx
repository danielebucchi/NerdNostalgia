"use client";

import { useRef, useState } from "react";
import { Lightbox } from "@/components/Lightbox";
import { thumbUrlsFor } from "@/lib/images";

interface Props {
  images: string[];
  title: string;
}

export function ArticleGallery({ images, title }: Props) {
  const [open, setOpen] = useState(false);
  const [startIndex, setStartIndex] = useState(0);
  // Indice slide corrente nello swipe mobile (per i pallini)
  const [current, setCurrent] = useState(0);
  const stripRef = useRef<HTMLDivElement>(null);

  const thumbs = thumbUrlsFor(images);
  const cover = images[0];

  function openAt(i: number) {
    setStartIndex(i);
    setOpen(true);
  }

  function onStripScroll() {
    const el = stripRef.current;
    if (!el) return;
    const idx = Math.round(el.scrollLeft / el.clientWidth);
    if (idx !== current) setCurrent(Math.max(0, Math.min(images.length - 1, idx)));
  }

  return (
    <>
      {/* ── Mobile: strip swipeable con scroll-snap + pallini ── */}
      <div className="sm:hidden">
        {images.length === 0 ? (
          <div className="card aspect-square w-full flex items-center justify-center">
            <span className="display text-ink-soft text-xl">No photo</span>
          </div>
        ) : (
          <>
            <div
              ref={stripRef}
              onScroll={onStripScroll}
              className="flex overflow-x-auto snap-x snap-mandatory rounded-3xl scrollbar-none"
              style={{ scrollbarWidth: "none" }}
              aria-label={`Galleria foto di ${title}, scorri per vedere le altre`}
            >
              {images.map((img, i) => (
                <button
                  key={img}
                  type="button"
                  onClick={() => openAt(i)}
                  className="w-full flex-shrink-0 snap-center card aspect-square flex items-center justify-center p-3 overflow-hidden cursor-zoom-in"
                  aria-label={`Ingrandisci foto ${i + 1} di ${images.length}`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={img}
                    alt={i === 0 ? title : ""}
                    loading={i === 0 ? "eager" : "lazy"}
                    className="max-w-full max-h-full object-contain"
                  />
                </button>
              ))}
            </div>
            {images.length > 1 && (
              <div className="flex justify-center gap-1.5 mt-3" aria-hidden="true">
                {images.map((_, i) => (
                  <span
                    key={i}
                    className={`h-2 rounded-full transition-all duration-200 ${
                      i === current ? "w-5 bg-pink-deep" : "w-2 bg-ink/20"
                    }`}
                  />
                ))}
              </div>
            )}
            <p className="text-[11px] text-ink-soft mt-2 text-center">
              {images.length > 1 ? "Scorri per le altre foto · " : ""}Tocca per ingrandire
            </p>
          </>
        )}
      </div>

      {/* ── Desktop: cover grande + griglia thumbnail ── */}
      <div className="hidden sm:block">
        <button
          type="button"
          onClick={() => images.length > 0 && openAt(0)}
          disabled={images.length === 0}
          className="card aspect-square w-full flex items-center justify-center p-4 overflow-hidden cursor-zoom-in group disabled:cursor-default relative"
          aria-label="Apri galleria a schermo intero"
        >
          {cover ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={cover}
                alt={title}
                className="max-w-full max-h-full object-contain transition-transform duration-300 group-hover:scale-[1.02]"
              />
              <span className="absolute bottom-3 right-3 inline-flex items-center gap-1 h-7 px-3 rounded-full bg-white/90 backdrop-blur ring-1 ring-ink/10 shadow-soft text-[11px] font-semibold text-ink opacity-0 group-hover:opacity-100 transition-opacity">
                🔍 Ingrandisci
              </span>
            </>
          ) : (
            <span className="display text-ink-soft text-xl">No photo</span>
          )}
        </button>

        {images.length > 1 && (
          <div className="mt-4 grid grid-cols-4 gap-3">
            {images.slice(1).map((img, i) => {
              const realIndex = i + 1;
              return (
                <button
                  key={img}
                  type="button"
                  onClick={() => openAt(realIndex)}
                  className="aspect-square card p-1 overflow-hidden cursor-zoom-in hover:ring-2 hover:ring-pink-deep/40 transition-all"
                  aria-label={`Apri immagine ${realIndex + 1}`}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={thumbs[realIndex] ?? img}
                    alt=""
                    className="w-full h-full object-cover rounded-lg"
                  />
                </button>
              );
            })}
          </div>
        )}
      </div>

      <Lightbox
        images={images}
        startIndex={startIndex}
        alt={title}
        open={open}
        onClose={() => setOpen(false)}
      />
    </>
  );
}
