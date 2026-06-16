import Link from "next/link";
import type { Article } from "@/lib/types";
import { formatPrice } from "@/lib/api";

const CONDITION_LABEL: Record<Article["condition"], string> = {
  NEW: "Nuovo",
  USED: "Usato",
  REFURBISHED: "Revisionato",
  FOR_PARTS: "Per pezzi",
};

// Chip uniformi (stile bottone ghost: bianco glassmorphism)
const NEUTRAL_CHIP = "chip-ghost";

const CATEGORY_CHIP: Record<string, string> = {
  "pokemon-cards": "chip-pink",
  "videogames": "chip-sky",
  "funko-pop": "chip-lilac",
};

export function ArticleCard({ article }: { article: Article }) {
  const cover = article.images?.[0];
  const categoryClass = article.category ? CATEGORY_CHIP[article.category] ?? "chip-mint" : "chip-mint";

  return (
    <Link href={`/articles/${article.id}`} className="card card-clickable block overflow-hidden">
      <div className="aspect-square w-full bg-cream/40 relative overflow-hidden">
        {cover ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={cover}
            alt={article.title}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-ink-soft">
            <span className="display text-3xl">?</span>
            <span className="text-xs uppercase tracking-wider mt-1">No photo</span>
          </div>
        )}

        {/* Riga unica di chip in alto, uniformi stile ghost */}
        <div className="absolute top-2 left-2 right-2 flex items-start gap-1 flex-wrap pointer-events-none">
          <span className={`chip ${NEUTRAL_CHIP} text-[10px]`}>
            {CONDITION_LABEL[article.condition]}
          </span>
          <span className="ml-auto flex gap-1 flex-wrap justify-end">
            {article.vinted_status === "LISTED" && article.vinted_url && (
              <span className={`chip ${NEUTRAL_CHIP} text-[10px]`}>🛍 Vinted</span>
            )}
            {article.ebay_status === "LISTED" && article.ebay_url && (
              <span className={`chip ${NEUTRAL_CHIP} text-[10px]`}>🏷 eBay</span>
            )}
          </span>
        </div>

        {article.status === "SOLD" && (
          <div className="absolute inset-0 bg-ink/55 backdrop-blur-[2px] flex items-center justify-center">
            <span className="display text-xl sm:text-2xl text-white bg-white/15 backdrop-blur-md rounded-full px-5 py-1.5 ring-1 ring-white/40">
              Venduto
            </span>
          </div>
        )}
      </div>

      <div className="p-4 flex flex-col gap-2">
        <h3 className="display text-base sm:text-lg text-ink leading-snug line-clamp-2 min-h-[48px]">
          {article.title}
        </h3>

        <div className="flex flex-wrap gap-2">
          {article.category && (
            <span className={`chip ${categoryClass}`}>{article.category.replace(/-/g, " ")}</span>
          )}
          {article.brand && (
            <span className="chip">{article.brand}</span>
          )}
        </div>

        <div className="flex items-end justify-between mt-2 pt-2 border-t-2 border-dashed border-ink/15">
          <span className="display text-2xl text-pink-deep">{formatPrice(article)}</span>
          <span className="text-xs text-ink-soft">vedi →</span>
        </div>
        {(article.vinted_price || article.ebay_price) && (
          <div className="text-[10px] text-ink-soft flex flex-wrap gap-x-2">
            {article.vinted_price && (
              <span>
                🛍 {formatPrice({ price: article.vinted_price, currency: article.currency })}
              </span>
            )}
            {article.ebay_price && (
              <span>
                🏷 {formatPrice({ price: article.ebay_price, currency: article.currency })}
              </span>
            )}
          </div>
        )}
      </div>
    </Link>
  );
}
