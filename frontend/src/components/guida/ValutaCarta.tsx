"use client";

import { useState } from "react";
import { Offerta, RISERVA } from "@/components/guida/Offerta";
import { VendilaANoi } from "@/components/guida/VendilaANoi";
import {
  CONDIZIONI, LINGUE, VERSIONI, euro, testoOfferta,
  type Condizione, type GuideCard, type Lingua, type Versione,
} from "@/lib/price-guide";

/* Chi vende sceglie versione (se ce n'e' piu' d'una), lingua e condizione
 * della sua copia: si vede il prezzo di mercato di quella copia e quanto diamo. */
export function ValutaCarta({ carta, compatto = false }: { carta: GuideCard; compatto?: boolean }) {
  const versioni = VERSIONI.filter((v) => Object.keys(carta.prices?.[v.id] ?? {}).length > 0);
  const [sceltaVersione, setVersione] = useState<Versione>(versioni[0]?.id ?? "normale");
  const versione = versioni.find((v) => v.id === sceltaVersione) ?? versioni[0];
  const prezzi = versione ? carta.prices?.[versione.id] ?? {} : {};

  const lingue = LINGUE.filter((l) => Object.keys(prezzi[l.id] ?? {}).length > 0);
  const [sceltaLingua, setLingua] = useState<Lingua>(lingue[0]?.id ?? "it");
  const lingua = lingue.find((l) => l.id === sceltaLingua) ?? lingue[0];

  const condizioni = CONDIZIONI.filter((c) => lingua && prezzi[lingua.id]?.[c.id]);
  const [sceltaCondizione, setCondizione] = useState<Condizione>(condizioni[0]?.id ?? "NM");
  const condizione = condizioni.find((c) => c.id === sceltaCondizione) ?? condizioni[0];

  const cella = versione && lingua && condizione ? prezzi[lingua.id]?.[condizione.id] : undefined;
  if (!versione || !lingua || !condizione || !cella) {
    return <p className="text-sm text-ink-soft">Nessun prezzo per copie italiane o inglesi.</p>;
  }
  const select = "rounded-xl border border-ink/15 bg-white px-3 py-2 text-sm text-ink";
  const descrizione = [versione.id !== "normale" ? versione.nome : null, lingua.nome.toLowerCase(), condizione.nome]
    .filter(Boolean).join(", ");

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {versioni.length > 1 && (
          <select value={versione.id} aria-label="Versione della carta" className={select}
            onChange={(e) => setVersione(e.target.value as Versione)}>
            {versioni.map((v) => <option key={v.id} value={v.id}>{v.nome}</option>)}
          </select>
        )}
        <select value={lingua.id} aria-label="Lingua della carta" className={select}
          onChange={(e) => setLingua(e.target.value as Lingua)}>
          {lingue.map((l) => <option key={l.id} value={l.id}>{l.nome}</option>)}
        </select>
        <select value={condizione.id} aria-label="Condizione della carta" className={select}
          onChange={(e) => setCondizione(e.target.value as Condizione)}>
          {condizioni.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
        </select>
      </div>
      {!compatto && (
        <p className="text-xs text-ink-soft">
          {versioni.length > 1 && <>{versione.spiegazione} </>}
          {condizione.spiegazione}
        </p>
      )}
      <p className="text-sm text-ink-soft">Valore di mercato: {euro(cella.price)}</p>
      <Offerta cella={cella} grande={!compatto} />
      {!cella.buy_none && (
        <>
          <p className="text-[11px] text-ink-soft">{RISERVA}</p>
          <VendilaANoi
            carta={`${carta.name} #${carta.number} – ${carta.set_name}, ${descrizione}`}
            offerta={testoOfferta(cella)}
            className={compatto ? "btn btn-ghost text-xs sm:text-sm" : "btn btn-primary"}
          />
        </>
      )}
    </div>
  );
}
