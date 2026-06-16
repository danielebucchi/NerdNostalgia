"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/admin-api";
import { formatPrice } from "@/lib/api";
import type { Article, MarketplaceStatus } from "@/lib/types";

export type MarketplaceKey = "vinted" | "ebay";

interface MarketplaceConfig {
  key: MarketplaceKey;
  label: string;
  emoji: string;
  newListingUrl: string;
  /** Testo aggiunto in fondo alla descrizione "copia formattata". */
  descriptionFooter: string;
}

const CONFIGS: Record<MarketplaceKey, MarketplaceConfig> = {
  vinted: {
    key: "vinted",
    label: "Vinted",
    emoji: "🛍",
    newListingUrl: "https://www.vinted.it/items/new",
    descriptionFooter:
      "Spedizione tracciata in tutta Italia.\nAltri pezzi nerd su nerdnostalgia.it",
  },
  ebay: {
    key: "ebay",
    label: "eBay",
    emoji: "🏷",
    newListingUrl: "https://www.ebay.it/sl/sell",
    descriptionFooter:
      "Spedizione tracciata in tutta Italia con corriere assicurato.\n" +
      "Altri pezzi nerd su nerdnostalgia.it",
  },
};

const STATUS_LABEL: Record<MarketplaceStatus, string> = {
  NOT_LISTED: "Non listato",
  LISTED: "Online",
  SOLD: "Venduto",
};

const STATUS_CHIP: Record<MarketplaceStatus, string> = {
  NOT_LISTED: "chip-lilac",
  LISTED: "chip-mint",
  SOLD: "chip-pink",
};

function getMarketplaceData(article: Article, key: MarketplaceKey) {
  if (key === "vinted") {
    return {
      status: article.vinted_status,
      url: article.vinted_url,
      syncedAt: article.vinted_synced_at,
    };
  }
  return {
    status: article.ebay_status,
    url: article.ebay_url,
    syncedAt: article.ebay_synced_at,
  };
}

function buildDescription(article: Article, footer: string): string {
  const lines: string[] = [];
  lines.push(article.title);
  lines.push("");
  if (article.description) {
    lines.push(article.description);
    lines.push("");
  }
  const meta: string[] = [];
  if (article.brand) meta.push(`Marca: ${article.brand}`);
  if (article.model) meta.push(`Modello: ${article.model}`);
  if (article.condition) meta.push(`Condizione: ${article.condition}`);
  if (article.dimensions_cm) meta.push(`Dimensioni: ${article.dimensions_cm} cm`);
  if (article.weight_kg) meta.push(`Peso: ${article.weight_kg} kg`);
  if (meta.length > 0) {
    lines.push(...meta);
    lines.push("");
  }
  lines.push(`Prezzo indicativo: ${formatPrice(article)}`);
  lines.push("");
  lines.push(footer);
  return lines.join("\n");
}

interface Props {
  article: Article;
  marketplace: MarketplaceKey;
  onUpdated: (updated: Article) => void;
}

export function MarketplaceSyncBox({ article, marketplace, onUpdated }: Props) {
  const config = CONFIGS[marketplace];
  const current = getMarketplaceData(article, marketplace);

  const [status, setStatus] = useState<MarketplaceStatus>(current.status);
  const [url, setUrl] = useState<string>(current.url ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setStatus(current.status);
    setUrl(current.url ?? "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [article.id, current.status, current.url]);

  const dirty = status !== current.status || (url || null) !== (current.url || null);

  function buildPayload(s: MarketplaceStatus, u: string | null) {
    return marketplace === "vinted"
      ? { vinted_status: s, vinted_url: u }
      : { ebay_status: s, ebay_url: u };
  }

  async function patch(payload: Record<string, unknown>) {
    setBusy(true);
    setError(null);
    try {
      const updated = await adminApi.patch<Article>(
        `/api/articles/${article.id}/${marketplace}`,
        payload,
      );
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleSave() {
    await patch(buildPayload(status, url.trim() || null));
  }

  async function quickAction(next: MarketplaceStatus) {
    await patch(buildPayload(next, url.trim() || null));
  }

  async function copyDescription() {
    const text = buildDescription(article, config.descriptionFooter);
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2200);
    } catch {
      setError("Impossibile copiare negli appunti (browser non lo supporta).");
    }
  }

  return (
    <div className="card p-5">
      <div className="flex items-baseline justify-between mb-3 gap-3 flex-wrap">
        <h2 className="display text-lg text-ink">
          {config.emoji} Sincronizza con {config.label}
        </h2>
        <span className={`chip ${STATUS_CHIP[status]}`}>{STATUS_LABEL[status]}</span>
      </div>

      <p className="text-sm text-ink-soft mb-4 leading-relaxed">
        Sincronizzazione assistita: prepari titolo e descrizione qui, pubblichi
        su {config.label} in un altro tab, poi torni e incolli l&apos;URL del
        listing. Marcandolo come <em>Venduto</em> l&apos;articolo viene marcato{" "}
        <code>SOLD</code> anche nel catalogo.
      </p>

      <div className="grid sm:grid-cols-2 gap-3 mb-4">
        <a
          href={config.newListingUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-primary text-sm justify-center"
        >
          {config.emoji} Apri {config.label} · Nuovo annuncio ↗
        </a>
        <button
          type="button"
          onClick={copyDescription}
          className="btn btn-ghost text-sm justify-center"
        >
          {copied ? "✓ Copiato!" : "📋 Copia descrizione formattata"}
        </button>
      </div>

      <label className="block mb-3">
        <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
          URL del listing {config.label}
        </span>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder={
            marketplace === "vinted"
              ? "https://www.vinted.it/items/123456789-…"
              : "https://www.ebay.it/itm/123456789"
          }
          className="input mt-1"
        />
      </label>

      <label className="block mb-4">
        <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
          Stato
        </span>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value as MarketplaceStatus)}
          className="input mt-1"
        >
          <option value="NOT_LISTED">Non listato</option>
          <option value="LISTED">Online su {config.label}</option>
          <option value="SOLD">Venduto su {config.label}</option>
        </select>
      </label>

      {error && <p className="text-pink-deep text-sm font-semibold mb-3">⚠ {error}</p>}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="btn btn-primary text-sm"
          onClick={handleSave}
          disabled={busy || !dirty}
        >
          {busy ? "Salvataggio…" : `Salva sync ${config.label}`}
        </button>
        {status !== "LISTED" && (
          <button
            type="button"
            className="btn btn-ghost text-sm"
            onClick={() => quickAction("LISTED")}
            disabled={busy}
          >
            Segna come ONLINE
          </button>
        )}
        {status !== "SOLD" && (
          <button
            type="button"
            className="btn btn-ghost text-sm"
            onClick={() => quickAction("SOLD")}
            disabled={busy}
          >
            Segna come VENDUTO
          </button>
        )}
        {status !== "NOT_LISTED" && (
          <button
            type="button"
            className="btn btn-ghost text-sm"
            onClick={() => quickAction("NOT_LISTED")}
            disabled={busy}
          >
            Reset
          </button>
        )}
      </div>

      {current.syncedAt && (
        <p className="text-xs text-ink-soft mt-3">
          Ultimo aggiornamento:{" "}
          {new Date(current.syncedAt).toLocaleString("it-IT")}
        </p>
      )}

      {current.url && (
        <p className="text-xs text-ink-soft mt-1">
          <a
            href={current.url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-pink-deep underline"
          >
            Apri il listing su {config.label} ↗
          </a>
        </p>
      )}

      <style>{`
        .input {
          display: block;
          width: 100%;
          padding: 0.55rem 0.8rem;
          border: 2px solid #3d2a5c;
          border-radius: 12px;
          background: #fffaf3;
          color: #3d2a5c;
          font-family: "Manrope", sans-serif;
          font-size: 0.95rem;
          outline: none;
        }
        .input:focus {
          box-shadow: 0 0 0 3px rgba(248, 168, 200, 0.45);
          border-color: #e879a8;
        }
      `}</style>
    </div>
  );
}
