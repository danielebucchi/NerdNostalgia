import Link from "next/link";
import { euro, type GuideCard } from "@/lib/price-guide";

/* Una carta nella griglia della guida prezzi. */
export function CartaTile({ carta, mostraSet = false }: { carta: GuideCard; mostraSet?: boolean }) {
  return (
    <Link
      href={`/prezzi-carte-pokemon/${carta.set_slug}/${carta.slug}`}
      className="card p-3 flex flex-col hover:-translate-y-0.5 transition-transform"
    >
      <div className="aspect-[63/88] rounded-xl bg-lilac/30 overflow-hidden flex items-center justify-center">
        {carta.image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={carta.image} alt={`${carta.name} ${carta.set_name}`} loading="lazy" className="w-full h-full object-contain" />
        ) : (
          <span className="text-ink-soft text-xs">#{carta.number}</span>
        )}
      </div>
      <p className="display text-sm text-ink mt-2 leading-tight">
        {carta.name} <span className="text-ink-soft">#{carta.number}</span>
      </p>
      {mostraSet && <p className="text-xs text-ink-soft truncate">{carta.set_name}</p>}
      <p className="text-sm font-bold text-pink-deep mt-auto pt-1">da {euro(carta.min_price)}</p>
      {carta.available && <span className="chip chip-mint text-[10px] mt-1 self-start">Disponibile da noi</span>}
    </Link>
  );
}
