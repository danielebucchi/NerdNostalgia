"use client";

import { useState } from "react";

type Marketplace = "vinted" | "ebay";

const META: Record<Marketplace, { src: string; alt: string; fallback: string }> = {
  vinted: { src: "/vinted.png", alt: "Vinted", fallback: "V" },
  ebay: { src: "/ebay.svg", alt: "eBay", fallback: "e" },
};

interface Props {
  marketplace: Marketplace;
  /** Altezza dell'immagine in px. La larghezza si adatta in proporzione. */
  height?: number;
  className?: string;
}

export function MarketplaceLogo({ marketplace, height = 16, className = "" }: Props) {
  const meta = META[marketplace];
  const [broken, setBroken] = useState(false);

  if (broken) {
    return (
      <span
        aria-label={meta.alt}
        title={meta.alt}
        className={
          "inline-flex items-center justify-center rounded-full bg-ink text-white text-[10px] font-bold leading-none " +
          className
        }
        style={{ width: height, height }}
      >
        {meta.fallback}
      </span>
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={meta.src}
      alt={meta.alt}
      title={meta.alt}
      className={"inline-block w-auto " + className}
      style={{ height }}
      onError={() => setBroken(true)}
    />
  );
}
