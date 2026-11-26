import { euro, type GuideCard } from "@/lib/price-guide";

/* Quanto diamo per una carta: la cifra per la singola, il prezzo al kg se va
 * a peso (sotto 0,50 €), o niente per le energie a peso. */
export function Offerta({ carta, grande = false }: { carta: GuideCard; grande?: boolean }) {
  const titolo = grande ? "display text-2xl text-ink" : "font-bold text-pink-deep";
  if (carta.buy_offer != null) {
    return (
      <div>
        <p className={titolo}>💰 Ti diamo fino a {euro(carta.buy_offer)}</p>
        {grande && (
          <p className="text-xs text-ink-soft mt-1">
            Per una copia in ottime condizioni: la cifra esatta la confermiamo dopo aver visto le foto.
          </p>
        )}
      </div>
    );
  }
  if (carta.buy_bulk) {
    return (
      <div>
        <p className={titolo}>⚖️ La compriamo a peso: {euro(carta.buy_bulk.eur_per_kg)} al kg</p>
        <p className="text-xs text-ink-soft mt-1">
          Vale meno di 50 centesimi: la prendiamo insieme alle altre carte {carta.buy_bulk.era}
          {grande ? " (un chilo sono circa 550 carte). Energie escluse." : "."}
        </p>
      </div>
    );
  }
  if (carta.buy_none) {
    return <p className="text-sm text-ink-soft">Le energie a peso non le compriamo.</p>;
  }
  return null;
}
