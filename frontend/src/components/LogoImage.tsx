"use client";

import { useState } from "react";

interface LogoImageProps {
  size?: number;
  className?: string;
  alt?: string;
}

// Sotto questa soglia (in px) usiamo SVG: 160KB, scala infinita, dettaglio
// indistinguibile dal PNG a queste dimensioni. Sopra preferiamo il PNG 1024x1024:
// l'SVG ottenuto via vtracer perde dettaglio nei tratti rispetto al raster originale.
const SVG_THRESHOLD = 96;

export function LogoImage({ size = 48, className = "", alt = "" }: LogoImageProps) {
  const preferred = size < SVG_THRESHOLD ? "/logo.svg" : "/logo.png";
  const [src, setSrc] = useState(preferred);

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt={alt}
      width={size}
      height={size}
      className={className}
      loading="lazy"
      decoding="async"
      onError={(e) => {
        // Fallback all'altro formato; se anche quello fallisce, nascondi
        if (src.endsWith(".svg")) {
          setSrc("/logo.png");
        } else if (src.endsWith(".png")) {
          setSrc("/logo.svg");
        } else {
          (e.currentTarget as HTMLImageElement).style.display = "none";
        }
      }}
    />
  );
}
