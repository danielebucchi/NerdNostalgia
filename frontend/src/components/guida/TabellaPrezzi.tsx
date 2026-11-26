import { CONDIZIONI, LINGUE, euro, type GuideCard } from "@/lib/price-guide";

/* Prezzo di mercato per condizione e lingua, con quanto diamo. */
export function TabellaPrezzi({ carta }: { carta: GuideCard }) {
  const lingue = LINGUE.filter((l) => Object.keys(carta.prices?.[l.id] ?? {}).length > 0);
  const righe = CONDIZIONI.filter((c) => lingue.some((l) => carta.prices?.[l.id]?.[c.id]));
  if (righe.length === 0) return null;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-ink-soft">
          <th className="py-2 pr-3 font-semibold">Condizione</th>
          {lingue.map((l) => <th key={l.id} className="py-2 pr-3 font-semibold">{l.nome}</th>)}
        </tr>
      </thead>
      <tbody>
        {righe.map((c) => (
          <tr key={c.id} className="border-t border-ink/10 align-top">
            <td className="py-2 pr-3">
              <span className="font-semibold text-ink">{c.nome}</span>
              <span className="block text-[11px] text-ink-soft">{c.spiegazione}</span>
            </td>
            {lingue.map((l) => {
              const cella = carta.prices?.[l.id]?.[c.id];
              return (
                <td key={l.id} className="py-2 pr-3">
                  {cella ? (
                    <>
                      <span className="font-bold text-ink">{euro(cella.price)}</span>
                      <span className="block text-[11px] text-pink-deep">
                        {cella.buy_offer != null ? `ti diamo fino a ${euro(cella.buy_offer)}`
                          : cella.buy_bulk ? `a peso, ${euro(cella.buy_bulk.eur_per_kg)}/kg`
                          : cella.buy_none ? "non la compriamo" : ""}
                      </span>
                    </>
                  ) : <span className="text-ink-soft">—</span>}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
