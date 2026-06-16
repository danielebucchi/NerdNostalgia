"use client";

import { useState } from "react";

interface Props {
  url: string;
  title: string;
  text?: string;
}

/**
 * Bottoni di condivisione articolo: WhatsApp, Telegram, copia link.
 * Usa Web Share API nativa se disponibile (tipico su mobile).
 */
export function ShareButtons({ url, title, text }: Props) {
  const [copied, setCopied] = useState(false);

  const shareText = text || title;
  const encodedUrl = encodeURIComponent(url);
  const encodedText = encodeURIComponent(`${shareText} — ${url}`);

  async function handleNativeShare() {
    if (typeof navigator === "undefined" || !("share" in navigator)) return;
    try {
      await navigator.share({ title, text: shareText, url });
    } catch {
      /* utente ha annullato */
    }
  }

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2200);
    } catch {
      // fallback: seleziona testo
      const input = document.createElement("input");
      input.value = url;
      document.body.appendChild(input);
      input.select();
      try {
        document.execCommand("copy");
        setCopied(true);
        setTimeout(() => setCopied(false), 2200);
      } finally {
        document.body.removeChild(input);
      }
    }
  }

  const hasNativeShare =
    typeof navigator !== "undefined" && "share" in navigator;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs uppercase tracking-wider text-ink-soft mr-1">
        Condividi:
      </span>

      <a
        href={`https://wa.me/?text=${encodedText}`}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-white/85 ring-1 ring-ink/10 backdrop-blur hover:bg-white hover:ring-ink/20 text-lg transition-all"
        aria-label="Condividi su WhatsApp"
        title="WhatsApp"
      >
        💬
      </a>

      <a
        href={`https://t.me/share/url?url=${encodedUrl}&text=${encodeURIComponent(shareText)}`}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-white/85 ring-1 ring-ink/10 backdrop-blur hover:bg-white hover:ring-ink/20 text-lg transition-all"
        aria-label="Condividi su Telegram"
        title="Telegram"
      >
        ✈
      </a>

      {hasNativeShare && (
        <button
          type="button"
          onClick={handleNativeShare}
          className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-white/85 ring-1 ring-ink/10 backdrop-blur hover:bg-white hover:ring-ink/20 text-lg transition-all"
          aria-label="Condividi"
          title="Altre app"
        >
          ↗
        </button>
      )}

      <button
        type="button"
        onClick={handleCopy}
        className={
          "inline-flex items-center gap-1.5 h-9 px-3 rounded-full text-xs font-semibold backdrop-blur transition-all " +
          (copied
            ? "bg-mint text-ink ring-1 ring-mint shadow-soft"
            : "bg-white/85 text-ink-soft ring-1 ring-ink/10 hover:bg-white hover:ring-ink/20")
        }
        aria-live="polite"
      >
        {copied ? "✓ Copiato" : "🔗 Copia link"}
      </button>
    </div>
  );
}
