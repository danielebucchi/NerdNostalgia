import Link from "next/link";
import type { Article } from "@/lib/types";
import { formatPrice } from "@/lib/api";

const CONDITION_LABEL: Record<Article["condition"], string> = {
  NEW: "Nuovo",
  USED: "Usato",
  REFURBISHED: "Revisionato",
  FOR_PARTS: "Per pezzi",
};

const CONDITION_CHIP: Record<Article["condition"], string> = {
  NEW: "chip-mint",
  USED: "chip-sky",
  REFURBISHED: "chip-star",
  FOR_PARTS: "chip-lilac",
};

const CATEGORY_CHIP: Record<string, string> = {
  "pokemon-cards": "chip-pink",
  "videogames": "chip-sky",
  "funko-pop": "chip-lilac",
};

export function ArticleCard({ article }: { article: Article }) {
  const cover = article.images?.[0];
  const conditionClass = CONDITION_CHIP[article.condition] ?? "chip-mint";
  const categoryClass = article.category ? CATEGORY_CHIP[article.category] ?? "chip-mint" : "chip-mint";

  return (
    <Link href={`/articles/${article.id}`} className="card card-clickable block overflow-hidden">
      <div className="aspect-square w-full bg-cream relative overflow-hidden border-b-2 border-ink/15">
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

        <span className={`chip ${conditionClass} absolute top-3 left-3`}>
          {CONDITION_LABEL[article.condition]}
        </span>

        {article.vinted_status === "LISTED" && article.vinted_url && (
          <span className="chip chip-pink absolute top-3 right-3 text-[10px]">
            🛍 Vinted
          </span>
        )}

        {article.status === "SOLD" && (
          <div className="absolute inset-0 bg-ink/70 flex items-center justify-center">
            <span className="display text-2xl text-pink rotate-[-6deg] border-2 border-pink rounded-chonk px-4 py-1 bg-ink">
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
      </div>
    </Link>
  );
}
