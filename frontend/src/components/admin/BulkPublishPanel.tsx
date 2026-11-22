"use client";
/**
 * Pubblicazione in blocco dalla lista articoli: gli articoli scelti su eBay
 * (prezzo suggerito o quello scritto nell'articolo) o su CardTrader (2° più
 * basso, solo carte già abbinate e con la condizione). Prima l'anteprima con
 * il prezzo di ognuno e chi resta fuori (e perché), poi si pubblica in fila.
 */
import { useEffect, useState } from "react";
import { adminApi } from "@/lib/admin-api";
import { inFila } from "@/lib/card-scanner";
import type { Article } from "@/lib/types";

type Canale = "ebay" | "cardtrader";

interface Riga {
  art: Article;
  prezzo: number | null;
  /** Perché resta fuori; null = si pubblica. */
  fuori: string | null;
  aggiorna: boolean;
}

interface AnteprimaEbay {
  price_eur: number | null;
  listing_id: string | null;
  collection_card: boolean;
}

const NOMI: Record<Canale, string> = { ebay: "eBay", cardtrader: "CardTrader" };

async function rigaEbay(a: Article): Promise<Riga> {
  if (a.status === "SOLD" || a.status === "ARCHIVED") return { art: a, prezzo: null, fuori: "venduto o archiviato", aggiorna: false };
  if (!a.images?.length) return { art: a, prezzo: null, fuori: "senza foto", aggiorna: false };
  const p = await adminApi.get<AnteprimaEbay>(`/api/articles/${a.id}/ebay/preview`);
  if (p.collection_card) return { art: a, prezzo: null, fuori: "carta della collezione: dallo scanner", aggiorna: false };
  if (p.price_eur == null) return { art: a, prezzo: null, fuori: "manca il prezzo", aggiorna: false };
  return { art: a, prezzo: p.price_eur, fuori: null, aggiorna: !!p.listing_id };
}

async function rigaCardTrader(a: Article): Promise<Riga> {
  if (a.status === "SOLD" || a.status === "ARCHIVED") return { art: a, prezzo: null, fuori: "venduto o archiviato", aggiorna: false };
  if (!a.cardtrader_blueprint_id) return { art: a, prezzo: null, fuori: "da abbinare a CardTrader nella scheda", aggiorna: false };
  if (!a.card_condition) return { art: a, prezzo: null, fuori: "manca la condizione della carta (scheda)", aggiorna: false };
  const qs = new URLSearchParams({
    blueprint_id: String(a.cardtrader_blueprint_id),
    condition: a.card_condition,
    language: a.card_language || "it",
    reverse: String(!!a.card_reverse),
    first_edition: String(!!a.card_first_edition),
  });
  try {
    const p = await adminApi.get<{ eur: number }>(`/api/cardtrader/suggested-price?${qs}`);
    return { art: a, prezzo: p.eur, fuori: null, aggiorna: !!a.cardtrader_product_id };
  } catch {
    return { art: a, prezzo: null, fuori: "nessuna inserzione di riferimento per il prezzo", aggiorna: false };
  }
}

export function BulkPublishPanel({
  articoli,
  onFinito,
}: {
  articoli: Article[];
  onFinito: () => void;
}) {
  const [canale, setCanale] = useState<Canale>("ebay");
  const [righe, setRighe] = useState<Riga[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [avanzamento, setAvanzamento] = useState<string | null>(null);
  const [esito, setEsito] = useState<string[] | null>(null);

  // Si rifà l'anteprima quando cambiano canale o articoli scelti, non quando
  // la lista si ricarica dopo aver pubblicato (l'esito resterebbe a metà).
  const ids = articoli.map((a) => a.id).join(",");
  useEffect(() => {
    let vivo = true;
    setRighe(null);
    setEsito(null);
    const fn = canale === "ebay" ? rigaEbay : rigaCardTrader;
    Promise.all(
      articoli.map((a) => fn(a).catch((e) => ({
        art: a, prezzo: null, fuori: e instanceof Error ? e.message : String(e), aggiorna: false,
      }))),
    ).then((r) => vivo && setRighe(r));
    return () => {
      vivo = false;
    };
  }, [canale, ids]); // eslint-disable-line react-hooks/exhaustive-deps

  const daFare = (righe ?? []).filter((r) => !r.fuori);

  async function pubblica() {
    setBusy(true);
    setEsito(null);
    const { errori } = await inFila(
      daFare,
      async (r) => {
        if (canale === "ebay") {
          await adminApi.post(`/api/articles/${r.art.id}/ebay/publish`);
        } else {
          await adminApi.post(`/api/cardtrader/publish/${r.art.id}`, {
            condition: r.art.card_condition,
            language: r.art.card_language || "it",
            reverse: !!r.art.card_reverse,
            first_edition: !!r.art.card_first_edition,
          });
        }
      },
      (n) => setAvanzamento(`${NOMI[canale]}: ${n}/${daFare.length}…`),
    );
    setAvanzamento(null);
    setEsito([
      `${NOMI[canale]}: ${daFare.length - errori.length}/${daFare.length} pubblicati`,
      ...errori.map((e) => `⚠ ${e.item.art.title}: ${e.error}`),
    ]);
    setBusy(false);
    onFinito();
  }

  return (
    <div className="card p-4 mb-4 space-y-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-semibold text-ink">Metti in vendita {articoli.length} articol{articoli.length === 1 ? "o" : "i"} su</span>
        {(["ebay", "cardtrader"] as Canale[]).map((c) => (
          <button key={c} type="button" onClick={() => setCanale(c)} disabled={busy}
            className={`chip cursor-pointer ${canale === c ? "chip-pink" : ""}`}>
            {NOMI[c]}
          </button>
        ))}
      </div>

      {!righe ? (
        <p className="text-ink-soft">Preparo l&apos;anteprima…</p>
      ) : (
        <ul className="divide-y divide-ink/5 max-h-80 overflow-y-auto">
          {righe.map((r) => (
            <li key={r.art.id} className="py-1.5 flex items-center justify-between gap-3">
              <span className={`truncate ${r.fuori ? "text-ink-soft line-through" : "text-ink"}`}>{r.art.title}</span>
              <span className="whitespace-nowrap text-right">
                {r.fuori ? (
                  <span className="text-xs text-ink-soft">{r.fuori}</span>
                ) : (
                  <>
                    <strong className="text-ink">{r.prezzo != null ? `${r.prezzo} €` : "—"}</strong>
                    {r.aggiorna && <span className="text-xs text-ink-soft"> · aggiorna</span>}
                  </>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <button type="button" className="btn btn-primary text-sm" disabled={busy || !daFare.length} onClick={pubblica}>
          {busy ? "…" : `Pubblica ${daFare.length} su ${NOMI[canale]}`}
        </button>
        <span className="text-xs text-ink-soft">
          {canale === "ebay"
            ? "Prezzo: quello scritto per eBay nell'articolo, se no il suggerito. Si cambia dalla scheda."
            : "Prezzo: il 2° più basso su CardTrader con le stesse caratteristiche."}
        </span>
      </div>
      {avanzamento && <p className="text-ink-soft">{avanzamento}</p>}
      {esito && (
        <div className="text-sm">
          {esito.map((r, i) => <p key={i} className={r.startsWith("⚠") ? "text-pink-deep" : "text-ink"}>{r}</p>)}
        </div>
      )}
    </div>
  );
}
