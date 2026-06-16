"use client";

interface LogoImageProps {
  size?: number;
  className?: string;
  alt?: string;
}

export function LogoImage({ size = 48, className = "", alt = "" }: LogoImageProps) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/logo.png"
      alt={alt}
      width={size}
      height={size}
      className={className}
      onError={(e) => {
        (e.currentTarget as HTMLImageElement).style.display = "none";
      }}
    />
  );
}
