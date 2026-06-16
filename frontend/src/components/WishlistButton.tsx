"use client";

import { useWishlist } from "@/lib/useWishlist";

interface Props {
  articleId: number;
  /** "icon" = solo cuore in cerchio (per le card), "full" = cuore + testo (per il dettaglio). */
  variant?: "icon" | "full";
  className?: string;
}

export function WishlistButton({ articleId, variant = "icon", className = "" }: Props) {
  const { has, toggle, hydrated } = useWishlist();
  const saved = has(articleId);

  // Prima dell'idratazione del client, evito mismatch SSR vs CSR usando
  // uno stato "non salvato" come default neutro.
  const isSaved = hydrated && saved;

  function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    toggle(articleId);
  }

  if (variant === "icon") {
    return (
      <button
        type="button"
        onClick={handleClick}
        aria-pressed={isSaved}
        aria-label={isSaved ? "Rimuovi dai preferiti" : "Aggiungi ai preferiti"}
        title={isSaved ? "Rimuovi dai preferiti" : "Aggiungi ai preferiti"}
        className={
          "inline-flex items-center justify-center w-9 h-9 rounded-full backdrop-blur transition-all " +
          (isSaved
            ? "bg-pink-deep text-white shadow-soft ring-1 ring-pink-deep"
            : "bg-white/85 text-ink-soft ring-1 ring-ink/10 hover:bg-white hover:text-pink-deep") +
          " " +
          className
        }
      >
        <span className="text-base leading-none">{isSaved ? "♥" : "♡"}</span>
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-pressed={isSaved}
      className={
        "btn text-sm " +
        (isSaved
          ? "btn-primary"
          : "btn-ghost") +
        " " +
        className
      }
    >
      <span className="text-base mr-1.5">{isSaved ? "♥" : "♡"}</span>
      {isSaved ? "Nei preferiti" : "Aggiungi ai preferiti"}
    </button>
  );
}
