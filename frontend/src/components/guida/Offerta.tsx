import { euro, type GuideCell } from "@/lib/price-guide";

export const RISERVA =
  "Valutazione indicativa: la confermiamo dopo aver visto la carta e ci riserviamo di cambiarla.";

/* Quanto diamo: la cifra per la singola, il prezzo al kg se va a peso (sotto
 * 0,50 €), o niente per le energie a peso. */
export function Offerta({ cella, grande = false }: { cella: GuideCell; grande?: boolean }) {
  const titolo = grande ? "display text-2xl text-ink" : "font-bold text-pink-deep";
  if (cella.buy_offer != null) {
    return <p className={titolo}>💰 Ti diamo fino a {euro(cella.buy_offer)}</p>;
  }
  if (cella.buy_bulk) {
    return (
      <div>
        <p className={titolo}>⚖️ La compriamo a peso: {euro(cella.buy_bulk.eur_per_kg)} al kg</p>
        <p className="text-xs text-ink-soft mt-1">
          Vale meno di 50 centesimi: la prendiamo insieme alle altre carte {cella.buy_bulk.era}
          {grande ? " (un chilo sono circa 550 carte). Energie escluse." : "."}
        </p>
      </div>
    );
  }
  if (cella.buy_none) {
    return <p className="text-sm text-ink-soft">Le energie a peso non le compriamo.</p>;
  }
  return null;
}
