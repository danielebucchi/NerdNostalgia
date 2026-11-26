"use client";

import { useMemo, useState } from "react";
import { Offerta, RISERVA } from "@/components/guida/Offerta";
import { VendilaANoi } from "@/components/guida/VendilaANoi";
import { CONDIZIONI, LINGUE, euro, testoOfferta, type Condizione, type GuideCard, type Lingua } from "@/lib/price-guide";

/* Chi vende sceglie lingua e condizione della sua copia: si vede il prezzo
 * di mercato di quella copia e quanto diamo. */
export function ValutaCarta({ carta, compatto = false }: { carta: GuideCard; compatto?: boolean }) {
  const lingue = LINGUE.filter((l) => Object.keys(carta.prices?.[l.id] ?? {}).length > 0);
  const [lingua, setLingua] = useState<Lingua>(lingue[0]?.id ?? "it");
  const condizioni = useMemo(
    () => CONDIZIONI.filter((c) => carta.prices?.[lingua]?.[c.id]),
    [carta.prices, lingua],
  );
  const [scelta, setScelta] = useState<Condizione>(condizioni[0]?.id ?? "NM");
  const condizione = condizioni.find((c) => c.id === scelta) ?? condizioni[0];
  const cella = condizione ? carta.prices?.[lingua]?.[condizione.id] : undefined;

  if (lingue.length === 0 || !condizione || !cella) {
    return <p className="text-sm text-ink-soft">Nessun prezzo per copie italiane o inglesi.</p>;
  }
  const nomeLingua = LINGUE.find((l) => l.id === lingua)?.nome.toLowerCase();
  const select = "rounded-xl border border-ink/15 bg-white px-3 py-2 text-sm text-ink";

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        <select value={lingua} aria-label="Lingua della carta" className={select}
          onChange={(e) => setLingua(e.target.value as Lingua)}>
          {lingue.map((l) => <option key={l.id} value={l.id}>{l.nome}</option>)}
        </select>
        <select value={condizione.id} aria-label="Condizione della carta" className={select}
          onChange={(e) => setScelta(e.target.value as Condizione)}>
          {condizioni.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
        </select>
      </div>
      {!compatto && <p className="text-xs text-ink-soft">{condizione.spiegazione}</p>}
      <p className="text-sm text-ink-soft">Valore di mercato: {euro(cella.price)}</p>
      <Offerta cella={cella} grande={!compatto} />
      {!cella.buy_none && (
        <>
          <p className="text-[11px] text-ink-soft">{RISERVA}</p>
          <VendilaANoi
            carta={`${carta.name} #${carta.number} – ${carta.set_name}, ${nomeLingua}, ${condizione.nome}`}
            offerta={testoOfferta(cella)}
            className={compatto ? "btn btn-ghost text-xs sm:text-sm" : "btn btn-primary"}
          />
        </>
      )}
    </div>
  );
}
