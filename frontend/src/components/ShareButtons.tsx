"use client";

import { useState } from "react";

interface Props {
  url: string;
  title: string;
  text?: string;
}

/** Link al gruppo WhatsApp NerdNostalgia. */
const WHATSAPP_GROUP_URL =
  "https://chat.whatsapp.com/GBvrghMizxfFRywmRIOrSq?s=cl&p=i&ilr=0";


export function ShareButtons({ url, title, text }: Props) {
  const [copied, setCopied] = useState(false);

  const shareText = text || title;

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
      <a
        href={WHATSAPP_GROUP_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-[#25D366] hover:bg-[#1eb957] shadow-soft transition-all"
        aria-label="Entra nel gruppo WhatsApp"
        title="Entra nel gruppo WhatsApp"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/whatsapp.png"
          alt=""
          className="w-5 h-5 object-contain"
        />
      </a>

      {hasNativeShare && (
        <button
          type="button"
          onClick={handleNativeShare}
          className="inline-flex items-center justify-center w-9 h-9 rounded-full bg-white/85 ring-1 ring-ink/10 backdrop-blur hover:bg-white hover:ring-ink/20 text-lg transition-all"
          aria-label="Condividi"
          title="Condividi"
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
