"use client";

/**
 * Box CardTrader sulla pagina admin articolo.
 * Flusso: gioco → espansione → cerca carta → abbina blueprint (salvato
 * sull'articolo) → mostra prezzo consigliato (4° più basso) → pubblica.
 * Solo per carte: CardTrader accetta solo prodotti agganciati a un blueprint.
 */
import { useEffect, useState } from "react";
import { adminApi } from "@/lib/admin-api";
import type { Article } from "@/lib/types";

interface Expansion { id: number; game_id: number; code: string; name: string }
interface Blueprint {
  id: number;
  name: string;
  version?: string;
  fixed_properties?: { collector_number?: string; [k: string]: unknown };
}
interface SuggestedPrice { eur: number; cents: number; position: number; total: number }

export function CardTraderBox({
  article,
  onUpdated,
}: {
  article: Article;
  onUpdated: (a: Article) => void;
}) {
  const [status, setStatus] = useState<null | { ok: boolean; detail?: string }>(null);
  // Espansioni del gioco predefinito (Pokémon), precaricate → dropdown
  // ricercabile con filtro client-side.
  const [allExpansions, setAllExpansions] = useState<Expansion[]>([]);
  const [expansionId, setExpansionId] = useState<number | null>(null);
  const [expQuery, setExpQuery] = useState("");
  const [expChosen, setExpChosen] = useState<string | null>(null);
  const [expOpen, setExpOpen] = useState(false);
  const [query, setQuery] = useState(article.title);
  const [results, setResults] = useState<Blueprint[]>([]);
  const [searching, setSearching] = useState(false);
  const [price, setPrice] = useState<SuggestedPrice | null>(null);
  const [priceOverride, setPriceOverride] = useState("");
  const [condition, setCondition] = useState("Near Mint");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const bpId = article.cardtrader_blueprint_id;
  const productId = article.cardtrader_product_id;

  // Prova connessione → precarica TUTTE le espansioni del gioco predefinito
  // (Pokémon) per la dropdown ricercabile
  useEffect(() => {
    adminApi
      .get<{ ok: boolean; detail?: string; default_game_id?: number | null }>(
        "/api/cardtrader/status",
      )
      .then((s) => {
        setStatus(s);
        if (s.ok) {
          const gid = s.default_game_id ?? 5;
          adminApi
            .get<Expansion[]>(`/api/cardtrader/expansions?game_id=${gid}&limit=5000`)
            .then(setAllExpansions)
            .catch(() => {});
        }
      })
      .catch(() => setStatus({ ok: false, detail: "non raggiungibile" }));
  }, []);

  // Prezzo consigliato quando c'è un blueprint abbinato
  useEffect(() => {
    if (!bpId) return;
    adminApi
      .get<SuggestedPrice>(`/api/cardtrader/suggested-price?blueprint_id=${bpId}`)
      .then(setPrice)
      .catch(() => setPrice(null));
  }, [bpId]);

  // Filtro client-side sulla lista precaricata (istantaneo, no round-trip)
  const expMatches = (() => {
    const q = expQuery.trim().toLowerCase();
    if (!q) return allExpansions.slice(0, 50);
    return allExpansions
      .filter((e) => e.name.toLowerCase().includes(q) || (e.code ?? "").toLowerCase().includes(q))
      .slice(0, 50);
  })();

  function chooseExpansion(e: Expansion) {
    setExpansionId(e.id);
    setExpChosen(e.name);
    setExpQuery("");
    setExpOpen(false);
  }

  async function autoResolve() {
    setSearching(true);
    setError(null);
    try {
      const r = await adminApi.get<{ candidates: Array<{ blueprint: Blueprint; expansion: { name: string }; number_match: boolean }> }>(
        `/api/cardtrader/resolve?article_id=${article.id}`,
      );
      // Riuso la lista risultati: mostro espansione + ✓ se numero combacia
      setResults(
        r.candidates.map((c) => ({
          ...c.blueprint,
          version: `${c.expansion.name}${c.number_match ? " · n° ✓" : ""}`,
        })),
      );
      if (r.candidates.length === 0) {
        setError("Nessun candidato: cerca a mano (gioco → espansione).");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSearching(false);
    }
  }

  async function search() {
    if (!expansionId) return;
    setSearching(true);
    setError(null);
    try {
      const r = await adminApi.get<Blueprint[]>(
        `/api/cardtrader/blueprints?expansion_id=${expansionId}&search=${encodeURIComponent(query.trim())}`,
      );
      setResults(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSearching(false);
    }
  }

  async function assign(blueprint: Blueprint | null) {
    setBusy(true);
    setError(null);
    try {
      const updated = await adminApi.patch<Article>(`/api/articles/${article.id}`, {
        cardtrader_blueprint_id: blueprint ? blueprint.id : null,
      });
      onUpdated(updated);
      setResults([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function publish() {
    if (!confirm("Pubblicare questa carta sul tuo shop CardTrader?")) return;
    setBusy(true);
    setError(null);
    try {
      const body: Record<string, unknown> = { condition, price_position: 4 };
      if (priceOverride.trim()) body.price_eur = Number(priceOverride);
      const res = await adminApi.post<{ product_id: number; price_eur: number }>(
        `/api/cardtrader/publish/${article.id}`,
        body,
      );
      const refreshed = await adminApi.get<Article>(`/api/articles/${article.id}`);
      onUpdated(refreshed);
      alert(`Pubblicato su CardTrader a €${res.price_eur} (prodotto #${res.product_id}).`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function unpublish() {
    if (!confirm("Rimuovere il prodotto da CardTrader? (l'abbinamento resta)")) return;
    setBusy(true);
    try {
      await adminApi.post(`/api/cardtrader/unpublish/${article.id}`, {});
      const refreshed = await adminApi.get<Article>(`/api/articles/${article.id}`);
      onUpdated(refreshed);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card p-5">
      <div className="flex items-baseline justify-between mb-3 gap-2 flex-wrap">
        <h2 className="display text-lg text-ink">🃏 CardTrader</h2>
        {status && (
          <span
            className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
              status.ok ? "bg-mint text-mint-deep" : "bg-pink-soft text-pink-deep"
            }`}
          >
            {status.ok ? "connesso" : `offline${status.detail ? `: ${status.detail}` : ""}`}
          </span>
        )}
      </div>

      {!status?.ok ? (
        <p className="text-sm text-ink-soft">
          CardTrader non configurato/raggiungibile. Imposta CARDTRADER_JWT.
        </p>
      ) : bpId ? (
        <div className="space-y-3">
          <div className="rounded-xl bg-mint/20 ring-1 ring-mint-deep/30 p-3 text-sm">
            <div className="flex items-center justify-between gap-2">
              <span className="text-ink">
                Abbinata al blueprint <strong className="font-mono">#{bpId}</strong>
              </span>
              <button
                type="button"
                onClick={() => assign(null)}
                disabled={busy}
                className="text-xs text-pink-deep hover:underline"
              >
                Scollega
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 items-end">
            <label className="block">
              <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
                Prezzo consigliato (4°)
              </span>
              <div className="text-2xl display text-pink-deep leading-tight">
                {price ? `€${price.eur.toFixed(2)}` : "—"}
              </div>
              {price && (
                <span className="text-[10px] text-ink-soft">
                  {price.position}° su {price.total} inserzioni
                </span>
              )}
            </label>
            <label className="block">
              <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
                Forza prezzo (opz.)
              </span>
              <input
                type="number"
                step="0.01"
                value={priceOverride}
                onChange={(e) => setPriceOverride(e.target.value)}
                placeholder={price ? String(price.eur) : "€"}
                className="ct-input mt-1"
              />
            </label>
          </div>

          <label className="block">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Condizione
            </span>
            <select
              value={condition}
              onChange={(e) => setCondition(e.target.value)}
              className="ct-input mt-1"
            >
              {["Mint", "Near Mint", "Slightly Played", "Moderately Played", "Played", "Poor"].map(
                (c) => <option key={c} value={c}>{c}</option>,
              )}
            </select>
          </label>

          <div className="flex flex-wrap gap-2 pt-1">
            <button
              type="button"
              onClick={publish}
              disabled={busy}
              className="btn btn-primary text-sm"
            >
              {productId ? "🔄 Aggiorna su CardTrader" : "🚀 Pubblica su CardTrader"}
            </button>
            {productId && (
              <button type="button" onClick={unpublish} disabled={busy} className="btn btn-ghost text-sm">
                Rimuovi
              </button>
            )}
          </div>
          {productId && (
            <p className="text-xs text-ink-soft">
              Online come prodotto <strong className="font-mono">#{productId}</strong>
              {article.cardtrader_synced_at &&
                ` · ${new Date(article.cardtrader_synced_at).toLocaleString("it-IT")}`}
            </p>
          )}
        </div>
      ) : (
        // ── Abbinamento: gioco → espansione → cerca carta ──
        <div className="space-y-3">
          <p className="text-sm text-ink-soft">
            Abbina questa carta al catalogo CardTrader per poterla pubblicare.
          </p>

          {/* Auto-match da collezione + numero già presenti sull'articolo */}
          {(article.card_collection || article.card_number) && (
            <button
              type="button"
              onClick={autoResolve}
              disabled={searching}
              className="btn btn-primary text-sm w-full"
              title={`Cerca da "${article.card_collection ?? ""}" n° ${article.card_number ?? ""}`}
            >
              {searching ? "Cerco…" : "✨ Trova automaticamente da collezione + numero"}
            </button>
          )}

          {/* Dropdown ricercabile con TUTTE le espansioni Pokémon (valore =
              id CardTrader). Digita per filtrare, clicca per selezionare. */}
          <div className="relative">
            <span className="text-xs font-bold uppercase tracking-wider text-ink-soft">
              Espansione (Pokémon)
            </span>
            <input
              value={expChosen ?? expQuery}
              onChange={(e) => {
                setExpChosen(null);
                setExpansionId(null);
                setExpQuery(e.target.value);
                setExpOpen(true);
              }}
              onFocus={() => setExpOpen(true)}
              onBlur={() => setTimeout(() => setExpOpen(false), 150)}
              placeholder={
                allExpansions.length
                  ? `Cerca fra ${allExpansions.length} espansioni…`
                  : "Carico espansioni…"
              }
              className="ct-input mt-1"
            />
            {expOpen && !expChosen && expMatches.length > 0 && (
              <div className="absolute z-10 left-0 right-0 mt-1 max-h-52 overflow-y-auto bg-white rounded-xl ring-1 ring-ink/15 shadow-hover">
                {expMatches.map((e) => (
                  <button
                    key={e.id}
                    type="button"
                    onMouseDown={(ev) => ev.preventDefault()}
                    onClick={() => chooseExpansion(e)}
                    className="w-full text-left px-3 py-2 hover:bg-pink-soft/40 text-sm"
                  >
                    <span className="text-ink font-semibold">{e.name}</span>
                    {e.code && <span className="text-ink-soft/60 text-[10px]"> ({e.code})</span>}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search()}
              placeholder="Nome o numero carta"
              className="ct-input flex-1"
            />
            <button
              type="button"
              onClick={search}
              disabled={!expansionId || searching}
              className="btn btn-ghost text-sm"
            >
              {searching ? "…" : "Cerca"}
            </button>
          </div>

          {results.length > 0 && (
            <div className="max-h-64 overflow-y-auto border border-ink/10 rounded-xl divide-y divide-ink/5">
              {results.map((b) => (
                <button
                  key={b.id}
                  type="button"
                  onClick={() => assign(b)}
                  disabled={busy}
                  className="w-full text-left px-3 py-2 hover:bg-pink-soft/40 text-sm"
                >
                  <span className="font-semibold text-ink">{b.name}</span>
                  {b.fixed_properties?.collector_number && (
                    <span className="text-ink-soft"> · {b.fixed_properties.collector_number}</span>
                  )}
                  {b.version && <span className="text-ink-soft block text-xs">{b.version}</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {error && <p className="text-pink-deep text-sm font-semibold mt-3">⚠ {error}</p>}

      <style>{`
        .ct-input {
          display: block; width: 100%;
          padding: 0.5rem 0.7rem;
          border: 1px solid rgba(61,42,92,0.12);
          border-radius: 12px; background: #fffaf3; color: #3d2a5c;
          font-size: 16px; outline: none;
        }
        .ct-input:focus { border-color:#e879a8; box-shadow:0 0 0 3px rgba(248,168,200,0.4); }
      `}</style>
    </div>
  );
}
