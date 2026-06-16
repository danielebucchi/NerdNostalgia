"use client";

import Link from "next/link";
import { useWishlist } from "@/lib/useWishlist";

interface Props {
  variant?: "desktop" | "mobile";
}

export function WishlistNavLink({ variant = "desktop" }: Props) {
  const { count, hydrated } = useWishlist();
  const showBadge = hydrated && count > 0;

  if (variant === "mobile") {
    return (
      <Link
        href="/preferiti"
        className="btn btn-ghost text-xs px-2.5 py-1.5 relative"
        aria-label="Preferiti"
      >
        ♥
        {showBadge && (
          <span className="absolute -top-1 -right-1 min-w-4 h-4 px-1 rounded-full bg-pink-deep text-white text-[9px] font-bold inline-flex items-center justify-center">
            {count}
          </span>
        )}
      </Link>
    );
  }

  return (
    <Link href="/preferiti" className="btn btn-ghost text-sm relative">
      <span className="mr-1">♥</span> Preferiti
      {showBadge && (
        <span className="ml-1.5 inline-flex items-center justify-center min-w-5 h-5 px-1 rounded-full bg-pink-deep text-white text-[10px] font-bold">
          {count}
        </span>
      )}
    </Link>
  );
}
