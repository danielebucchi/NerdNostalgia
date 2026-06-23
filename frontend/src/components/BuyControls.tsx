"use client";

import { useState } from "react";
import { MarketplaceLogo } from "@/components/MarketplaceLogo";
import { PurchaseDialog } from "@/components/PurchaseDialog";
import { paymentsEnabled } from "@/lib/features";
import { paypalEnabled } from "@/lib/paypal";
import { useCart } from "@/lib/cart";
import type { Article } from "@/lib/types";

interface Props {
  article: Article;
}

/**
 * Controlli di acquisto inline accanto al prezzo articolo:
 *  - bottoni Vinted / eBay (link diretti ai marketplace)
 *  - bottone "Paga con PayPal" → apre PurchaseDialog (raccoglie dati,
 *    crea ordine PENDING, manda email, apre paypal.me)
 *  - bottone "Aggiungi al carrello" → toggle articolo nel carrello
 */
export function BuyControls({ article }: Props) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const { has, toggle } = useCart();
  const ship = article.shipping_price ? Number(article.shipping_price) : 5;
  const grandTotal = Number(article.price || 0) + ship;
  const inCart = has(article.id);

  return (
    <>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-3">
        {article.vinted_status === "LISTED" && article.vinted_url && (
          <a
            href={article.vinted_url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Acquista questo articolo su Vinted"
            className="btn btn-vinted text-sm font-bold px-4 py-2.5 inline-flex items-center gap-2"
          >
            <MarketplaceLogo marketplace="vinted" height={16} />
            <span>Su Vinted</span>
            <span aria-hidden="true">→</span>
          </a>
        )}

        {article.ebay_status === "LISTED" && article.ebay_url && (
          <a
            href={article.ebay_url}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Acquista questo articolo su eBay"
            className="btn btn-ebay text-sm font-bold px-4 py-2.5 inline-flex items-center gap-2"
          >
            <MarketplaceLogo marketplace="ebay" height={16} />
            <span>Su eBay</span>
            <span aria-hidden="true">→</span>
          </a>
        )}

        {paymentsEnabled() && paypalEnabled() && article.status === "PUBLISHED" && (
          <button
            type="button"
            onClick={() => setDialogOpen(true)}
            aria-label={`Acquista questo articolo via PayPal a ${grandTotal.toFixed(2)} euro`}
            className="btn btn-paypal text-sm font-bold px-4 py-2.5 inline-flex items-center gap-2"
          >
            <span>Paga € {grandTotal.toFixed(2)} su PayPal</span>
            <span aria-hidden="true">→</span>
          </button>
        )}

        {paymentsEnabled() && article.status === "PUBLISHED" && (
          <button
            type="button"
            onClick={() => toggle(article.id)}
            aria-pressed={inCart}
            className={`btn text-sm font-bold px-4 py-2.5 inline-flex items-center gap-2 ${
              inCart ? "btn-primary" : "btn-ghost"
            }`}
          >
            <span aria-hidden="true">🛒</span>
            <span>{inCart ? "Nel carrello" : "Aggiungi al carrello"}</span>
          </button>
        )}
      </div>

      <p className="text-xs text-ink-soft mt-2">
        Prezzo: € {Number(article.price).toFixed(2)}
        {paymentsEnabled() && (
          <>
            {" "}·{" "}
            <strong className="text-ink">Spedizione: € {ship.toFixed(2)}</strong>{" "}
            · totale € {grandTotal.toFixed(2)}
          </>
        )}
      </p>
      {paymentsEnabled() && paypalEnabled() && article.status === "PUBLISHED" && (
        <>
          <div className="mt-3 inline-flex items-center gap-2 text-xs rounded-full bg-white text-ink px-3 py-1.5 font-semibold ring-2 ring-mint-deep shadow-soft">
            <span aria-hidden="true" className="text-base">🤝</span>
            <span>
              Consegna a mano <strong className="text-mint-deep">gratuita</strong>{" "}
              a Livorno/Pisa
              <span className="font-normal text-ink-soft ml-1">
                (no spedizione)
              </span>
            </span>
          </div>
          <p className="text-[11px] text-ink-soft mt-2 leading-snug">
            💡 Su PayPal scegli{" "}
            <strong className="text-[#003087]">
              &quot;Amico o familiare&quot;
            </strong>{" "}
            per evitare le commissioni.
          </p>
        </>
      )}

      {paymentsEnabled() && (
        <PurchaseDialog
          open={dialogOpen}
          onClose={() => setDialogOpen(false)}
          articles={[article]}
          shippingTotal={ship}
        />
      )}
    </>
  );
}
