"use client";

import Link from "next/link";
import { useCart } from "@/lib/cart";
import { paymentsEnabled } from "@/lib/features";

interface Props {
  variant?: "desktop" | "mobile";
}

export function CartNavLink({ variant = "desktop" }: Props) {
  const { count, hydrated } = useCart();
  if (!paymentsEnabled()) return null;
  const showBadge = hydrated && count > 0;
  const label = `Carrello${showBadge ? ` (${count})` : ""}`;

  if (variant === "mobile") {
    return (
      <Link
        href="/carrello"
        className="btn btn-ghost text-xs px-2.5 py-1.5 relative"
        aria-label={label}
        title={label}
      >
        🛒
        {showBadge && (
          <span className="absolute -top-1 -right-1 min-w-[18px] h-[18px] rounded-full bg-pink-deep text-white text-[10px] font-bold flex items-center justify-center px-1">
            {count}
          </span>
        )}
      </Link>
    );
  }

  return (
    <Link
      href="/carrello"
      className="btn btn-ghost text-sm relative inline-flex items-center gap-1.5"
    >
      <span aria-hidden="true">🛒</span>
      <span>Carrello</span>
      {showBadge && (
        <span className="min-w-[20px] h-[20px] rounded-full bg-pink-deep text-white text-[11px] font-bold flex items-center justify-center px-1.5">
          {count}
        </span>
      )}
    </Link>
  );
}
