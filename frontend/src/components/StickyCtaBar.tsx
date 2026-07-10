"use client";

/**
 * Barra CTA fissa in basso sulla pagina articolo (solo mobile): prezzo
 * sempre visibile + azione principale (WhatsApp se configurato + Chiedi
 * info). Mentre e' montata alza i FAB (classe body) per non coprirli.
 */
import { useEffect, useState } from "react";
import { InquiryDialog } from "@/components/InquiryDialog";
import { formatPrice } from "@/lib/api";
import { useSettings, whatsappUrl } from "@/lib/settings-context";
import type { Article } from "@/lib/types";

export function StickyCtaBar({ article }: { article: Article }) {
  const { contactWhatsapp } = useSettings();
  const [inquiryOpen, setInquiryOpen] = useState(false);

  // Alza i FAB Donazione/WhatsApp sopra la barra finche' e' montata
  useEffect(() => {
    document.body.classList.add("has-ctabar");
    return () => document.body.classList.remove("has-ctabar");
  }, []);

  const sold = article.status === "SOLD";
  const waText = `Ciao! Sono interessato a "${article.title}" — ${
    typeof window !== "undefined" ? window.location.href : ""
  }`;
  const waUrl = contactWhatsapp ? whatsappUrl(contactWhatsapp, waText) : null;

  return (
    <>
      <div
        className="sm:hidden fixed bottom-0 inset-x-0 z-40 bg-white/95 backdrop-blur-xl border-t border-ink/10 px-4 py-2.5 flex items-center gap-3"
        style={{ paddingBottom: "calc(0.625rem + env(safe-area-inset-bottom))" }}
      >
        <div className="min-w-0">
          <p className="display text-xl text-pink-deep leading-none">
            {formatPrice(article)}
          </p>
          {sold && (
            <p className="text-[10px] font-bold uppercase tracking-wider text-ink-soft">
              Venduto
            </p>
          )}
        </div>
        <div className="flex-1" />
        {!sold && waUrl && (
          <a
            href={waUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="btn text-sm font-bold px-4 py-2.5 inline-flex items-center gap-1.5 bg-[#25D366] text-white"
            aria-label="Scrivimi su WhatsApp per questo articolo"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/whatsapp.png" alt="" width={16} height={16} />
            WhatsApp
          </a>
        )}
        {!sold && (
          <button
            type="button"
            onClick={() => setInquiryOpen(true)}
            className="btn btn-primary text-sm font-bold px-4 py-2.5"
          >
            💬 Info
          </button>
        )}
      </div>

      <InquiryDialog
        open={inquiryOpen}
        onClose={() => setInquiryOpen(false)}
        articleId={article.id}
        articleTitle={article.title}
      />
    </>
  );
}
