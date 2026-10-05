"use client";

import { useState } from "react";
import { MarketplaceLogo } from "@/components/MarketplaceLogo";
import { PurchaseDialog } from "@/components/PurchaseDialog";
import { FREE_SHIPPING_FROM, shippingFor, useCart } from "@/lib/cart";
import { useSettings, whatsappUrl } from "@/lib/settings-context";
import type { Article } from "@/lib/types";

interface Props {
  article: Article;
}

/**
 * Controlli di acquisto inline accanto al prezzo articolo:
 *  - bottoni Vinted / eBay (link diretti ai marketplace)
 *  - bottone WhatsApp (se contact_whatsapp e' configurato nelle settings)
 *  - bottone "Paga con PayPal" → apre PurchaseDialog (raccoglie dati,
 *    crea ordine PENDING, manda email, apre paypal.me)
 *  - bottone "Aggiungi al carrello" → toggle articolo nel carrello
 */
export function BuyControls({ article }: Props) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const { has, toggle } = useCart();
  const { paymentsEnabled, contactWhatsapp, freeShippingAll } = useSettings();
  // Spedizione a scaglioni sul prezzo: comprando questo pezzo da solo e'
  // questa, ma nel carrello cambia col totale (e sopra i 200 € sparisce).
  const price = Number(article.price || 0);
  const ship = shippingFor(price, undefined, freeShippingAll);
  const grandTotal = price + ship;
  const inCart = has(article.id);

  const waText = `Ciao! Sono interessato a "${article.title}" — ${
    typeof window !== "undefined" ? window.location.href : ""
  }`;
  const waUrl = contactWhatsapp ? whatsappUrl(contactWhatsapp, waText) : null;

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

        {waUrl && article.status === "PUBLISHED" && (
          <a
            href={waUrl}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Contattaci su WhatsApp per questo articolo"
            className="btn text-sm font-bold px-4 py-2.5 inline-flex items-center gap-2 bg-[#25D366] text-white hover:brightness-105"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/whatsapp.png" alt="" width={16} height={16} />
            <span>WhatsApp</span>
          </a>
        )}

        {paymentsEnabled && article.status === "PUBLISHED" && (
          <button
            type="button"
            onClick={() => setDialogOpen(true)}
            aria-label={`Acquista questo articolo a ${grandTotal.toFixed(2)} euro`}
            className="btn btn-primary text-sm font-bold px-4 py-2.5 inline-flex items-center gap-2"
          >
            <span>Acquista € {grandTotal.toFixed(2)}</span>
            <span aria-hidden="true">→</span>
          </button>
        )}

        {paymentsEnabled && article.status === "PUBLISHED" && (
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
        Prezzo: € {price.toFixed(2)}
        {paymentsEnabled && (
          <>
            {" "}·{" "}
            <strong className="text-ink">
              Spedizione:{" "}
              {ship === 0 ? "gratis" : `€ ${ship.toFixed(2)}`}
            </strong>{" "}
            · totale € {grandTotal.toFixed(2)}
          </>
        )}
      </p>
      {paymentsEnabled && article.status === "PUBLISHED" && (
        <p className="text-[11px] text-mint-deep font-semibold mt-1.5 leading-snug">
          {freeShippingAll
            ? "🚚 Spedizione gratuita su tutto il catalogo"
            : ship > 0
              ? `🚚 Spedizione gratuita per ordini da € ${FREE_SHIPPING_FROM.toFixed(2)}`
              : ""}
        </p>
      )}
      {paymentsEnabled && (
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
