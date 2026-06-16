"use client";

import { useState } from "react";
import { Lightbox } from "@/components/Lightbox";
import { thumbUrlsFor } from "@/lib/images";

interface Props {
  images: string[];
  title: string;
}

export function ArticleGallery({ images, title }: Props) {
  const [open, setOpen] = useState(false);
  const [startIndex, setStartIndex] = useState(0);

  const thumbs = thumbUrlsFor(images);
  const cover = images[0];
  const coverThumb = thumbs[0];

  function openAt(i: number) {
    setStartIndex(i);
    setOpen(true);
  }

  return (
    <>
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

      <Lightbox
        images={images}
        startIndex={startIndex}
        alt={title}
        open={open}
        onClose={() => setOpen(false)}
      />

      {/* Hint per dare contesto alla copertina su mobile */}
      <p className="text-[11px] text-ink-soft mt-2 sm:hidden text-center">
        Tocca la foto per ingrandirla {coverThumb && images.length > 1 ? "· scorri per le altre" : ""}
      </p>
    </>
  );
}
