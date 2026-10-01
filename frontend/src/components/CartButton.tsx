"use client";

import { useCart } from "@/lib/cart";
import { useSettings } from "@/lib/settings-context";

interface Props {
  articleId: number;
  /** Mostrato solo per gli articoli acquistabili: niente carrello sui VENDUTI. */
  purchasable: boolean;
  /** "icon" = pallino 🛒 per le card del catalogo, "full" = con etichetta. */
  variant?: "icon" | "full";
  className?: string;
}

/**
 * Aggiungi/togli dal carrello direttamente dal catalogo, senza passare dalla
 * scheda articolo.
 *
 * Sta dentro una card che e' tutta un <Link>: per questo il click ferma la
 * propagazione, altrimenti aggiungere al carrello navigherebbe via.
 */
export function CartButton({
  articleId,
  purchasable,
  variant = "icon",
  className = "",
}: Props) {
  const { has, toggle, hydrated } = useCart();
  const { paymentsEnabled } = useSettings();

  // Prima dell'idratazione niente stato "nel carrello": il server non conosce
  // il localStorage e un mismatch farebbe sfarfallare la card.
  const inCart = hydrated && has(articleId);

  if (!paymentsEnabled || !purchasable) return null;

  function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();
    toggle(articleId);
  }

  const label = inCart ? "Togli dal carrello" : "Aggiungi al carrello";

  if (variant === "icon") {
    return (
      <button
        type="button"
        onClick={handleClick}
        aria-pressed={inCart}
        aria-label={label}
        title={label}
        className={
          "inline-flex items-center justify-center w-9 h-9 rounded-full backdrop-blur transition-all " +
          (inCart
            ? "bg-mint-deep text-white shadow-soft ring-1 ring-mint-deep"
            : "bg-white/85 text-ink-soft ring-1 ring-ink/10 hover:bg-white hover:text-mint-deep") +
          " " +
          className
        }
      >
        <span className="text-base leading-none" aria-hidden="true">
          {inCart ? "✓" : "🛒"}
        </span>
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      aria-pressed={inCart}
      className={
        "btn text-sm " + (inCart ? "btn-primary" : "btn-ghost") + " " + className
      }
    >
      <span className="text-base mr-1.5" aria-hidden="true">
        {inCart ? "✓" : "🛒"}
      </span>
      {inCart ? "Nel carrello" : "Aggiungi al carrello"}
    </button>
  );
}
