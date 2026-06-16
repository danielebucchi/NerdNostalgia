"use client";

import { useEffect, useState } from "react";
import { adminApi } from "@/lib/admin-api";
import { formatPrice } from "@/lib/api";
import type { Article, VintedStatus } from "@/lib/types";

const VINTED_NEW_URL = "https://www.vinted.it/items/new";

const STATUS_LABEL: Record<VintedStatus, string> = {
  NOT_LISTED: "Non listato",
  LISTED: "Online su Vinted",
  SOLD: "Venduto su Vinted",
};

const STATUS_CHIP: Record<VintedStatus, string> = {
  NOT_LISTED: "chip-lilac",
  LISTED: "chip-mint",
  SOLD: "chip-pink",
};

function buildVintedDescription(article: Article): string {
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
  lines.push("Spedizione tracciata in tutta Italia.");
  lines.push("Altri pezzi nerd su nerdnostalgia.it");
  return lines.join("\n");
}

interface Props {
  article: Article;
  onUpdated: (updated: Article) => void;
}

export function VintedSyncBox({ article, onUpdated }: Props) {
  const [status, setStatus] = useState<VintedStatus>(article.vinted_status);
  const [url, setUrl] = useState<string>(article.vinted_url ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setStatus(article.vinted_status);
    setUrl(article.vinted_url ?? "");
  }, [article.id, article.vinted_status, article.vinted_url]);

  const dirty =
    status !== article.vinted_status || (url || null) !== (article.vinted_url || null);

  async function handleSave() {
    setBusy(true);
    setError(null);
    try {
      const updated = await adminApi.patch<Article>(
        `/api/articles/${article.id}/vinted`,
        { vinted_status: status, vinted_url: url.trim() || null },
      );
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function quickAction(next: VintedStatus) {
    setBusy(true);
    setError(null);
    try {
      const updated = await adminApi.patch<Article>(
        `/api/articles/${article.id}/vinted`,
        { vinted_status: next, vinted_url: url.trim() || null },
      );
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function copyDescription() {
    const text = buildVintedDescription(article);
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
        <h2 className="display text-lg text-ink">Sincronizza con Vinted</h2>
        <span className={`chip ${STATUS_CHIP[status]}`}>{STATUS_LABEL[status]}</span>
      </div>

      <p className="text-sm text-ink-soft mb-4 leading-relaxed">
        Vinted non offre API pubbliche: la sincronizzazione è assistita.
        Prepari titolo e descrizione qui, pubblichi su Vinted in un altro tab,
        poi torni e incolli l&apos;URL del listing. Quando lo segni come
        <em> Venduto</em>, l&apos;articolo viene marcato <code>SOLD</code> anche
        nel catalogo.
      </p>

      <div className="grid sm:grid-cols-2 gap-3 mb-4">
        <a
          href={VINTED_NEW_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-primary text-sm justify-center"
        >
          🛍 Apri Vinted · Nuovo annuncio ↗
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
          URL del listing Vinted
        </span>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.vinted.it/items/123456789-…"
          className="input mt-1"
        />
      </label>

      <label className="block mb-4">
        <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
          Stato
        </span>
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value as VintedStatus)}
          className="input mt-1"
        >
          <option value="NOT_LISTED">Non listato</option>
          <option value="LISTED">Online su Vinted</option>
          <option value="SOLD">Venduto su Vinted</option>
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
          {busy ? "Salvataggio…" : "Salva sync Vinted"}
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

      {article.vinted_synced_at && (
        <p className="text-xs text-ink-soft mt-3">
          Ultimo aggiornamento:{" "}
          {new Date(article.vinted_synced_at).toLocaleString("it-IT")}
        </p>
      )}

      {article.vinted_url && (
        <p className="text-xs text-ink-soft mt-1">
          <a
            href={article.vinted_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-pink-deep underline"
          >
            Apri il listing su Vinted ↗
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
