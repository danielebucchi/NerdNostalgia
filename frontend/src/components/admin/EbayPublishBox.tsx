"use client";
/**
 * Box "eBay automatico" sulla pagina admin articolo: mette l'articolo su
 * eBay tramite API (un'inserzione, niente varianti), con le regole delle
 * carte dello scanner. Prezzo e categoria si vedono prima di pubblicare.
 * Il prezzo scritto nel box eBay manuale vince sul calcolato.
 */
import { useCallback, useEffect, useState } from "react";
import { adminApi } from "@/lib/admin-api";
import type { Article } from "@/lib/types";

interface Anteprima {
  price_eur: number | null;
  price_suggested: number | null;
  price_manual: boolean;
  category_id: string | null;
  category_name: string | null;
  listing_id: string | null;
  url: string | null;
  collection_card: boolean;
  /** Carta dello scanner: la sua inserzione eBay (null se non e' su eBay). */
  collection_ebay_url: string | null;
  collection_ebay_variations: boolean;
}

const eur = (v: number | null) => (v == null ? "—" : `${v.toFixed(0)} €`);

export function EbayPublishBox({
  article,
  onUpdated,
}: {
  article: Article;
  onUpdated: () => void;
}) {
  const [info, setInfo] = useState<Anteprima | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nota, setNota] = useState<string | null>(null);
  // Prezzo da mandare: parte da quello in uso (scritto o suggerito).
  const [prezzo, setPrezzo] = useState("");
  useEffect(() => {
    if (info?.price_eur != null) setPrezzo(String(info.price_eur));
  }, [info?.price_eur]);

  const carica = useCallback(() => {
    adminApi
      .get<Anteprima>(`/api/articles/${article.id}/ebay/preview`)
      .then(setInfo)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, [article.id]);

  // Si ricarica quando cambia l'articolo (prezzo, prezzo eBay scritto a mano...).
  useEffect(carica, [carica, article.price, article.ebay_price, article.status]);

  async function esegui(fn: () => Promise<unknown>, ok: string) {
    setBusy(true);
    setError(null);
    setNota(null);
    try {
      await fn();
      setNota(ok);
      carica();
      onUpdated();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  /** Il body della pubblicazione: il prezzo scritto, o null = il suggerito
   * (che segue la regola se cambia il prezzo dell'articolo). */
  function corpo() {
    const v = Number(prezzo.replace(",", "."));
    const scelto = prezzo.trim() && Number.isFinite(v) && v > 0 ? v : null;
    return { price: scelto != null && scelto !== info?.price_suggested ? scelto : null };
  }

  const online = !!info?.listing_id;
  const venduto = article.status === "SOLD" || article.status === "ARCHIVED";

  return (
    <div className="card p-5">
      <div className="flex items-baseline justify-between mb-3 gap-2 flex-wrap">
        <h2 className="display text-lg text-ink">🤖 eBay automatico</h2>
        {(online || info?.collection_ebay_url) && (
          <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-mint text-mint-deep">in vendita</span>
        )}
      </div>

      {info?.collection_card ? (
        <div className="text-sm space-y-2">
          {info.collection_ebay_url ? (
            <p className="text-ink">
              ✅ In vendita su eBay come carta della collezione
              {info.collection_ebay_variations ? " (inserzione con varianti)" : ""}:{" "}
              <a href={info.collection_ebay_url} target="_blank" rel="noreferrer" className="underline text-lilac-deep">
                vedi su eBay ↗
              </a>
            </p>
          ) : (
            <p className="text-ink-soft">Non è su eBay.</p>
          )}
          <p className="text-ink-soft">
            È una carta della collezione: su eBay si mette, si aggiorna e si ritira dallo scanner carte (Collezione).
          </p>
        </div>
      ) : (
        <div className="space-y-3 text-sm">
          <div className="grid grid-cols-2 gap-3">
            <label className="block">
              <span className="block text-xs font-bold uppercase tracking-wider text-ink-soft">Prezzo eBay (€)</span>
              <input type="number" min={1} step={1} inputMode="numeric" className="input mt-1 !w-28 text-lg"
                value={prezzo} onChange={(e) => setPrezzo(e.target.value)}
                placeholder={info?.price_suggested != null ? String(info.price_suggested) : "€"} aria-label="Prezzo eBay" />
              <span className="block text-[11px] text-ink-soft mt-1">
                Suggerito {eur(info?.price_suggested ?? null)} (commissione eBay e regola delle carte)
                {info?.price_suggested != null && Number(prezzo) !== info.price_suggested && (
                  <>
                    {" · "}
                    <button type="button" className="underline" onClick={() => setPrezzo(String(info.price_suggested))}>
                      usa il suggerito
                    </button>
                  </>
                )}
              </span>
            </label>
            <div>
              <span className="block text-xs font-bold uppercase tracking-wider text-ink-soft">Categoria eBay</span>
              <span className="text-ink">
                {info?.category_id ? `${info.category_name ?? ""} (${info.category_id})` : "la propone eBay dal titolo"}
              </span>
            </div>
          </div>

          {online ? (
            <div className="flex flex-wrap gap-2 items-center">
              {info?.url && (
                <a href={info.url} target="_blank" rel="noreferrer" className="underline text-lilac-deep">
                  vedi su eBay ↗
                </a>
              )}
              <button type="button" className="btn btn-primary text-sm" disabled={busy || venduto}
                onClick={() => esegui(() => adminApi.post(`/api/articles/${article.id}/ebay/publish`, corpo()), "inserzione aggiornata")}>
                {busy ? "…" : "Aggiorna su eBay"}
              </button>
              <button type="button" className="btn btn-ghost text-sm" disabled={busy}
                onClick={() => esegui(() => adminApi.delete(`/api/articles/${article.id}/ebay/publish`), "tolto da eBay")}>
                Ritira
              </button>
            </div>
          ) : (
            <button type="button" className="btn btn-primary text-sm w-full" disabled={busy || venduto || info?.price_eur == null}
              onClick={() => esegui(() => adminApi.post(`/api/articles/${article.id}/ebay/publish`, corpo()), "in vendita su eBay")}>
              {busy ? "Pubblico…" : "Pubblica su eBay"}
            </button>
          )}
          <p className="text-[11px] text-ink-soft">
            Su eBay i prezzi sono senza centesimi: quello scritto va all&apos;euro sopra. Venduto sul sito o su Vinted, archiviato o eliminato: l&apos;inserzione eBay si ritira da sola.
          </p>
        </div>
      )}
      {nota && <p className="text-sm text-ink mt-3">{nota}</p>}
      {error && <p className="text-pink-deep text-sm font-semibold mt-3">⚠ {error}</p>}
    </div>
  );
}
