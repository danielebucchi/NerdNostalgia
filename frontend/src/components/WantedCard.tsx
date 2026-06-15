import Link from "next/link";
import type { WantedItem } from "@/lib/types";
import { formatMaxPrice } from "@/lib/api";

const CONDITION_LABEL: Record<string, string> = {
  NEW: "Nuovo",
  USED: "Usato",
  REFURBISHED: "Revisionato",
  FOR_PARTS: "Per pezzi",
};

const CATEGORY_CHIP: Record<string, string> = {
  "pokemon-cards": "chip-pink",
  videogames: "chip-sky",
  "funko-pop": "chip-lilac",
};

export function WantedCard({ item }: { item: WantedItem }) {
  const maxPrice = formatMaxPrice(item);
  const categoryClass = item.category ? CATEGORY_CHIP[item.category] ?? "chip-mint" : "chip-mint";
  const urgent = item.priority >= 50;

  return (
    <Link
      href={`/cerco-compro/${item.id}`}
      className="card card-clickable block p-5 h-full flex flex-col"
    >
      <div className="flex items-start gap-2 mb-3">
        {urgent && (
          <span className="chip chip-star whitespace-nowrap">🔥 con urgenza</span>
        )}
        {item.category && (
          <span className={`chip ${categoryClass}`}>{item.category.replace(/-/g, " ")}</span>
        )}
      </div>

      <h3 className="display text-lg text-ink leading-snug mb-2">{item.title}</h3>

      {item.description && (
        <p className="text-ink-soft text-sm leading-relaxed line-clamp-3 mb-3">
          {item.description}
        </p>
      )}

      <div className="mt-auto pt-3 border-t-2 border-dashed border-ink/15 flex items-end justify-between gap-2">
        <div className="text-xs text-ink-soft">
          {item.preferred_condition && (
            <div>
              <span className="uppercase tracking-wider">Condizione</span>
              <div className="text-ink font-semibold text-sm">
                {CONDITION_LABEL[item.preferred_condition] ?? item.preferred_condition}
              </div>
            </div>
          )}
        </div>
        <div className="text-right">
          {maxPrice ? (
            <>
              <span className="text-xs uppercase tracking-wider text-ink-soft block">Offro fino a</span>
              <span className="display text-xl text-pink-deep">{maxPrice}</span>
            </>
          ) : (
            <span className="chip chip-lilac text-[0.65rem]">da concordare</span>
          )}
        </div>
      </div>
    </Link>
  );
}
